from dataclasses import dataclass

from PIL import Image, ImageOps


class QRDecodeError(Exception):
    """Raised when no readable QR payload can be extracted."""


@dataclass
class QRDecodeResult:
    payload: str
    engine: str


def decode_qr_image(image_path):
    """
    Decode a QR code using pyzbar first, then OpenCV's QRCodeDetector.
    The OpenCV fallback keeps demos working on machines without the zbar DLL.
    """
    errors = []

    try:
        from pyzbar.pyzbar import decode as zbar_decode

        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            decoded = zbar_decode(image)
            if decoded:
                payload = decoded[0].data.decode("utf-8", errors="replace").strip()
                if payload:
                    return QRDecodeResult(payload=payload, engine="pyzbar")
    except Exception as exc:
        errors.append(f"pyzbar: {exc}")

    try:
        import cv2

        image = cv2.imread(str(image_path))
        if image is None:
            raise QRDecodeError("OpenCV could not read the uploaded image.")

        detector = cv2.QRCodeDetector()
        payload, points, _ = detector.detectAndDecode(image)
        if payload and points is not None:
            return QRDecodeResult(payload=payload.strip(), engine="opencv")
    except Exception as exc:
        errors.append(f"opencv: {exc}")

    detail = "; ".join(errors) if errors else "No QR content found."
    raise QRDecodeError(f"Unable to decode a QR code from this image. {detail}")
