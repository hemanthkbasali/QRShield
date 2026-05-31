"""
brand_detector.py — Brand impersonation detection for QRShield.

Strategy (three-layer, no heavyweight dependency):
  1. Exact-match check  — catches obvious clones.
  2. Levenshtein distance — standard edit-distance via difflib SequenceMatcher
     (stdlib, no extra install) + optional fast path with rapidfuzz when available.
  3. Homoglyph normalisation — common digit/character substitutions
     (0→o, 1→l/i, 3→e, 4→a, 5→s, 6→g, 7→t, 8→b, @→a, etc.) are
     collapsed before comparison so "paypa1.com" → "paypal.com" is caught.

A match is reported when the *normalised* edit-distance similarity ≥ THRESHOLD
and the extracted second-level domain is NOT the protected brand itself.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum similarity (0.0–1.0) to flag a domain as a brand impersonation.
# 0.82 catches 1-2 char mutations without too many false positives.
SIMILARITY_THRESHOLD = 0.82

# Protected brands: (canonical_domain_sld, display_name, official_tld)
# sld = second-level domain (the part before the last dot in the registered domain)
PROTECTED_BRANDS: list[tuple[str, str, str]] = [
    ("amazon",    "Amazon",    "amazon.com"),
    ("google",    "Google",    "google.com"),
    ("microsoft", "Microsoft", "microsoft.com"),
    ("paypal",    "PayPal",    "paypal.com"),
    ("github",    "GitHub",    "github.com"),
    ("facebook",  "Facebook",  "facebook.com"),
    ("instagram", "Instagram", "instagram.com"),
    ("apple",     "Apple",     "apple.com"),
    ("netflix",   "Netflix",   "netflix.com"),
    ("twitter",   "Twitter",   "twitter.com"),
    ("linkedin",  "LinkedIn",  "linkedin.com"),
    ("dropbox",   "Dropbox",   "dropbox.com"),
    ("spotify",   "Spotify",   "spotify.com"),
    ("adobe",     "Adobe",     "adobe.com"),
    ("samsung",   "Samsung",   "samsung.com"),
    ("chase",     "Chase Bank","chase.com"),
    ("wellsfargo","Wells Fargo","wellsfargo.com"),
    ("binance",   "Binance",   "binance.com"),
    ("coinbase",  "Coinbase",  "coinbase.com"),
    ("steam",     "Steam",     "steampowered.com"),
]

# Common homoglyph / leet-speak substitutions that attackers use.
# Applied before Levenshtein comparison so e.g. "g00gle" → "google".
_HOMOGLYPH_MAP: dict[str, str] = {
    "0": "o",
    "1": "l",
    "2": "z",
    "3": "e",
    "4": "a",
    "5": "s",
    "6": "g",
    "7": "t",
    "8": "b",
    "9": "g",
    "@": "a",
    "!": "i",
    "$": "s",
    "+": "t",
    "vv": "w",   # multi-char handled below
    "rn": "m",
}

# Multi-char sequences must be handled separately (order matters: longest first)
_MULTI_CHAR_SUBS: list[tuple[str, str]] = [
    ("vv", "w"),
    ("rn", "m"),
]


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

class BrandMatch(NamedTuple):
    brand_name: str           # e.g. "PayPal"
    official_domain: str      # e.g. "paypal.com"
    candidate_sld: str        # e.g. "paypa1"
    similarity: float         # 0.0–1.0
    normalised_candidate: str # after homoglyph collapse
    method: str               # "exact_homoglyph" | "fuzzy"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_unicode(text: str) -> str:
    """NFKD-decompose and strip combining marks, then ASCII-fold."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower()


def _homoglyph_collapse(text: str) -> str:
    """Replace common leet/homoglyph chars so similarity is brand-centric."""
    result = _normalise_unicode(text)
    # Multi-char first (order: longest → shortest)
    for src, dst in _MULTI_CHAR_SUBS:
        result = result.replace(src, dst)
    # Single-char map
    return "".join(_HOMOGLYPH_MAP.get(ch, ch) for ch in result)


def _levenshtein_similarity(a: str, b: str) -> float:
    """
    Return normalised similarity in [0, 1] using stdlib SequenceMatcher
    (Ratcliff/Obershelp algorithm, O(n²)).  If rapidfuzz is installed it is
    used instead for speed, but both give comparable results for short strings.
    """
    if not a or not b:
        return 0.0
    try:
        import rapidfuzz.fuzz as _rf  # type: ignore
        return _rf.ratio(a, b) / 100.0
    except ImportError:
        pass
    return SequenceMatcher(None, a, b).ratio()


def _extract_sld(hostname: str) -> str:
    """
    Extract the second-level domain from a hostname.
    e.g. "login.paypa1.com" → "paypa1"
         "www.arnazon.co.uk" → "arnazon"
    We strip leading 'www.' then take the penultimate label.
    """
    hostname = hostname.lower().strip()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    labels = hostname.split(".")
    # Need at least SLD + TLD
    if len(labels) >= 2:
        return labels[-2]
    return labels[0] if labels else ""


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------

def detect_brand_impersonation(hostname: str) -> BrandMatch | None:
    """
    Check *hostname* against all protected brands.

    Returns a BrandMatch if an impersonation attempt is detected, else None.
    Genuine matches (exact domain match to the protected brand) are ignored.
    """
    if not hostname:
        return None

    candidate_sld = _extract_sld(hostname)
    if not candidate_sld:
        return None

    normalised = _homoglyph_collapse(candidate_sld)

    best: BrandMatch | None = None
    best_sim = 0.0

    for brand_sld, brand_name, official_domain in PROTECTED_BRANDS:
        # Skip if this IS the genuine domain (exact SLD match after normalisation)
        if candidate_sld == brand_sld:
            return None

        # --- layer 1: homoglyph-collapsed exact match ---
        if normalised == brand_sld:
            match = BrandMatch(
                brand_name=brand_name,
                official_domain=official_domain,
                candidate_sld=candidate_sld,
                similarity=1.0,
                normalised_candidate=normalised,
                method="exact_homoglyph",
            )
            return match  # can't get better than this

        # --- layer 2: fuzzy Levenshtein on *both* raw and normalised ---
        sim_raw  = _levenshtein_similarity(candidate_sld, brand_sld)
        sim_norm = _levenshtein_similarity(normalised,    brand_sld)
        sim = max(sim_raw, sim_norm)

        if sim >= SIMILARITY_THRESHOLD and sim > best_sim:
            best_sim = sim
            best = BrandMatch(
                brand_name=brand_name,
                official_domain=official_domain,
                candidate_sld=candidate_sld,
                similarity=sim,
                normalised_candidate=normalised,
                method="fuzzy",
            )

    return best
