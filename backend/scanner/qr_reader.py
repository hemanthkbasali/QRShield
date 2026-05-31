"""
qr_reader.py — robust multi-engine QR decoder.

Engine order per preprocessing variant:
  1. pyzbar        — fastest when libzbar DLL is present
  2. opencv        — QRCodeDetectorAruco (OpenCV 4.8+) then QRCodeDetector fallback
  3. zxingcpp      — optional pure-C++ binding (pip install zxingcpp), no DLL dependency

Preprocessing variants tried in order:
  original-rgb · grayscale · adaptive-threshold · CLAHE ·
  contrast-boost · 2x-upscale · 3x-upscale

If every engine/variant combination fails, QRDecodeError is raised with a
diagnostic string automatically stored in scan.threats[0]["description"].
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class QRDecodeError(Exception):
    """Raised when no readable QR payload can be extracted from the image."""


@dataclass
class QRDecodeResult:
    payload: str
    engine: str


def decode_qr_image(image_path: Path) -> QRDecodeResult:
    """
    Decode a QR code from *image_path* using multiple engines and preprocessing
    variants. Raises QRDecodeError when all attempts fail.
    """
    image_path = Path(image_path)
    logger.info("[QR] decode start  path=%s", image_path)

    if not image_path.exists():
        raise QRDecodeError(f"Uploaded image file not found on disk: {image_path}")

    try:
        variants = _build_variants(image_path)
    except Exception as exc:
        logger.error("[QR] preprocessing error: %s", exc)
        raise QRDecodeError(f"Image preprocessing failed: {exc}") from exc

    logger.info("[QR] variants prepared  count=%d", len(variants))

    for label, pil_img, cv_img in variants:
        for fn, tag in (
            (_try_pyzbar,   "pyzbar"),
            (_try_opencv,   "opencv"),
            (_try_zxingcpp, "zxingcpp"),
        ):
            payload = fn(pil_img, cv_img, label)
            if payload:
                engine_tag = f"{tag}/{label}"
                logger.info("[QR] success  engine=%s  payload=%r", engine_tag, payload[:80])
                return QRDecodeResult(payload=payload, engine=engine_tag)

    logger.warning("[QR] all engines failed  file=%s  variants=%d", image_path.name, len(variants))
    raise QRDecodeError(
        f"No QR code found after {len(variants)} preprocessing variants "
        "(tried pyzbar, opencv, zxingcpp). "
        "Ensure the image contains a clear, unobstructed QR symbol."
    )


# ---------------------------------------------------------------------------
# Preprocessing helpers
# ---------------------------------------------------------------------------

def _pil_to_cv(pil_img: Image.Image) -> np.ndarray:
    """Convert a PIL Image to an OpenCV-compatible numpy array."""
    mode = pil_img.mode
    arr = np.array(pil_img)
    if mode == "RGB":
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    if mode == "L":
        return arr
    return np.array(pil_img.convert("L"))


def _build_variants(image_path: Path):
    """
    Return list of (label, pil_image, cv_image) tuples.
    Both forms are pre-built so every engine has what it needs.
    """
    # --- base load ---
    with Image.open(image_path) as raw:
        pil_rgb = ImageOps.exif_transpose(raw).convert("RGB")

    cv_bgr = cv2.imread(str(image_path))
    if cv_bgr is None:
        # Handles non-ASCII / UNC paths that cv2.imread rejects on Windows
        logger.debug("[QR] cv2.imread returned None — falling back to PIL conversion")
        cv_bgr = _pil_to_cv(pil_rgb)

    cv_gray = cv2.cvtColor(cv_bgr, cv2.COLOR_BGR2GRAY)
    pil_gray = Image.fromarray(cv_gray)

    variants: list[tuple[str, Image.Image, np.ndarray]] = []

    # 1. original RGB
    variants.append(("original-rgb", pil_rgb, cv_bgr))

    # 2. grayscale
    variants.append(("grayscale", pil_gray, cv_gray))

    # 3. adaptive threshold — good for printed / unevenly lit QR codes
    thresh = cv2.adaptiveThreshold(
        cv_gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        11, 2,
    )
    variants.append(("adaptive-thresh", Image.fromarray(thresh), thresh))

    # 4. CLAHE contrast equalisation
    clahe_img = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(cv_gray)
    variants.append(("clahe", Image.fromarray(clahe_img), clahe_img))

    # 5. PIL contrast boost — helps faded / low-contrast prints
    contrast_pil = ImageEnhance.Contrast(pil_rgb).enhance(2.0)
    variants.append(("contrast-boost", contrast_pil, _pil_to_cv(contrast_pil)))

    # 6. 2× upscale — helps with small / low-resolution QR images
    h, w = cv_gray.shape
    up2 = cv2.resize(cv_gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    variants.append(("2x-upscale", Image.fromarray(up2), up2))

    # 7. 3× upscale
    up3 = cv2.resize(cv_gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    variants.append(("3x-upscale", Image.fromarray(up3), up3))

    return variants


# ---------------------------------------------------------------------------
# Engine wrappers — each returns payload string or None
# ---------------------------------------------------------------------------

def _try_pyzbar(pil_img: Image.Image | None, cv_img, label: str) -> str | None:
    try:
        from pyzbar.pyzbar import decode as zbar_decode
        if pil_img is None:
            return None
        results = zbar_decode(pil_img)
        if results:
            payload = results[0].data.decode("utf-8", errors="replace").strip()
            if payload:
                logger.debug("[QR] pyzbar hit  variant=%s", label)
                return payload
    except ImportError as exc:
        logger.debug("[QR] pyzbar unavailable (DLL/import): %s", exc)
    except Exception as exc:
        logger.debug("[QR] pyzbar error  variant=%s  error=%s", label, exc)
    return None


def _try_opencv(pil_img, cv_img: np.ndarray | None, label: str) -> str | None:
    if cv_img is None:
        return None
    try:
        detectors = []
        if hasattr(cv2, "QRCodeDetectorAruco"):
            detectors.append(("aruco", cv2.QRCodeDetectorAruco()))
        detectors.append(("std", cv2.QRCodeDetector()))

        for det_name, detector in detectors:
            try:
                payload, points, _ = detector.detectAndDecode(cv_img)
                if payload and points is not None:
                    payload = payload.strip()
                    logger.debug("[QR] opencv/%s hit  variant=%s", det_name, label)
                    return payload
            except Exception as exc:
                logger.debug("[QR] opencv/%s error  variant=%s  error=%s", det_name, label, exc)
    except Exception as exc:
        logger.debug("[QR] opencv error  variant=%s  error=%s", label, exc)
    return None


def _try_zxingcpp(pil_img: Image.Image | None, cv_img, label: str) -> str | None:
    try:
        import zxingcpp  # optional — pip install zxingcpp
        if pil_img is None:
            return None
        results = zxingcpp.read_barcodes(pil_img)
        for r in results:
            text = getattr(r, "text", "") or ""
            if text.strip():
                logger.debug("[QR] zxingcpp hit  variant=%s", label)
                return text.strip()
    except ImportError:
        pass  # not installed — silently skip
    except Exception as exc:
        logger.debug("[QR] zxingcpp error  variant=%s  error=%s", label, exc)
    return None
