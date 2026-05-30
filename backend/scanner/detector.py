import ipaddress
import re
import unicodedata
from urllib.parse import parse_qs, urlparse

from .utils import clamp, shannon_entropy


SUSPICIOUS_KEYWORDS = {
    "account",
    "alert",
    "bank",
    "billing",
    "bonus",
    "claim",
    "confirm",
    "crypto",
    "free",
    "gift",
    "login",
    "password",
    "secure",
    "signin",
    "support",
    "update",
    "verify",
    "wallet",
}

FAKE_LOGIN_PAYMENT_KEYWORDS = {
    "2fa",
    "auth",
    "checkout",
    "credential",
    "invoice",
    "otp",
    "payment",
    "paypal",
    "refund",
    "reset",
    "security",
    "unlock",
}

SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "cutt.ly",
    "rebrand.ly",
    "shorturl.at",
    "s.id",
    "lnkd.in",
    "rb.gy",
}


def normalize_url(value):
    value = (value or "").strip()
    if not value:
        return "", None

    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", value):
        parsed = urlparse(value)
        return value, parsed

    if re.match(r"^[\w.-]+\.[a-zA-Z]{2,}(/.*)?$", value):
        normalized = f"http://{value}"
        return normalized, urlparse(normalized)

    return value, urlparse(value)


def is_ip_host(hostname):
    if not hostname:
        return False
    try:
        ipaddress.ip_address(hostname.strip("[]"))
        return True
    except ValueError:
        return False


def unicode_spoof_evidence(hostname):
    if not hostname:
        return []

    evidence = []
    scripts = set()
    non_ascii = []
    for char in hostname:
        if ord(char) <= 127:
            continue
        non_ascii.append(char)
        name = unicodedata.name(char, "")
        for script in ("CYRILLIC", "GREEK", "HEBREW", "ARABIC", "DEVANAGARI"):
            if script in name:
                scripts.add(script.title())

    labels = hostname.split(".")
    if any(label.startswith("xn--") for label in labels):
        evidence.append("punycode IDN label")
    if non_ascii:
        evidence.append(f"non-ASCII characters: {''.join(sorted(set(non_ascii)))[:12]}")
    if len(scripts) > 1 or (scripts and any(char.isascii() and char.isalpha() for char in hostname)):
        evidence.append(f"mixed script domain: {', '.join(sorted(scripts))}")
    if any(unicodedata.category(char) in {"Cf", "Mn"} for char in hostname):
        evidence.append("hidden or combining Unicode marks")
    return evidence


def add_threat(threats, title, description, severity, weight, evidence=""):
    threats.append(
        {
            "title": title,
            "description": description,
            "severity": severity,
            "weight": weight,
            "evidence": evidence,
        }
    )


def recommendation_for(threat_title):
    mapping = {
        "Missing HTTPS": "Do not submit credentials or payment data unless the destination uses HTTPS.",
        "IP-based destination": "Avoid IP-address QR links unless they are from a known internal system.",
        "Suspicious keyword pattern": "Verify the destination in a browser before entering sensitive information.",
        "URL shortener": "Expand shortened URLs with a trusted preview service before opening.",
        "Excessive URL length": "Do not trust long QR URLs without manually checking the base domain first.",
        "Random-looking domain": "Check the brand's official domain manually instead of trusting the QR code.",
        "Unicode spoofing pattern": "Type the official domain manually when a QR URL contains internationalized or lookalike characters.",
        "Special character abuse": "Inspect the full URL for redirects, @ signs, and misleading subdomains.",
        "Credential/payment lure": "Never enter OTP, password, card, or wallet information from an unsolicited QR.",
        "Redirect-heavy query": "Avoid QR links that immediately forward through redirect or tracking parameters.",
        "Non-URL QR content": "Treat non-URL payloads as data only; do not execute copied commands or scripts.",
    }
    return mapping.get(threat_title, "Validate the sender and destination before interacting with this QR code.")


def analyze_payload(payload):
    normalized, parsed = normalize_url(payload)
    threats = []
    score = 0
    metadata = {
        "input_type": "url" if parsed and parsed.netloc else "text",
        "scheme": parsed.scheme if parsed else "",
        "hostname": parsed.hostname if parsed else "",
        "path_length": len(parsed.path) if parsed else 0,
        "query_params": len(parse_qs(parsed.query)) if parsed and parsed.query else 0,
    }

    if not parsed or not parsed.netloc:
        add_threat(
            threats,
            "Non-URL QR content",
            "The QR payload is not a standard URL. It may be plain text, a command, or app-specific data.",
            "low",
            35,
            payload[:120],
        )
        score += 35
        return build_result(payload, "", score, threats, metadata)

    hostname = (parsed.hostname or "").lower()
    host_labels = [label for label in hostname.split(".") if label]
    domain_without_tld = host_labels[-2] if len(host_labels) >= 2 else hostname
    full_url_lower = normalized.lower()
    url_length = len(normalized)
    query_length = len(parsed.query or "")
    metadata.update(
        {
            "url_length": url_length,
            "query_length": query_length,
            "domain": hostname,
        }
    )

    if parsed.scheme != "https":
        add_threat(
            threats,
            "Missing HTTPS",
            "The destination does not use a secure HTTPS transport layer.",
            "medium",
            22,
            parsed.scheme or "no scheme",
        )
        score += 22

    if is_ip_host(hostname):
        add_threat(
            threats,
            "IP-based destination",
            "The QR opens a raw IP address instead of a recognizable domain.",
            "high",
            24,
            hostname,
        )
        score += 24

    if url_length > 120 or query_length > 90:
        weight = 24 if url_length > 220 or query_length > 180 else 14
        add_threat(
            threats,
            "Excessive URL length",
            "The QR destination is unusually long, which can hide redirects, tracking chains, or deceptive parameters.",
            "high" if weight >= 24 else "medium",
            weight,
            f"{url_length} characters",
        )
        score += weight

    keyword_hits = sorted(word for word in SUSPICIOUS_KEYWORDS if word in full_url_lower)
    if keyword_hits:
        weight = min(24, 8 + len(keyword_hits) * 4)
        add_threat(
            threats,
            "Suspicious keyword pattern",
            "The URL contains terms commonly used in phishing lures.",
            "medium",
            weight,
            ", ".join(keyword_hits[:8]),
        )
        score += weight

    payment_hits = sorted(word for word in FAKE_LOGIN_PAYMENT_KEYWORDS if word in full_url_lower)
    if payment_hits:
        weight = min(28, 12 + len(payment_hits) * 5)
        add_threat(
            threats,
            "Credential/payment lure",
            "The URL appears to reference login, payment, authentication, or recovery flows.",
            "high",
            weight,
            ", ".join(payment_hits[:8]),
        )
        score += weight

    shortener_host = hostname[4:] if hostname.startswith("www.") else hostname
    if shortener_host in SHORTENERS:
        add_threat(
            threats,
            "URL shortener",
            "Shortened URLs hide the final destination and are frequently abused in QR phishing.",
            "high",
            24,
            shortener_host,
        )
        score += 24

    entropy = shannon_entropy(domain_without_tld)
    digit_ratio = sum(ch.isdigit() for ch in domain_without_tld) / max(len(domain_without_tld), 1)
    hyphen_count = domain_without_tld.count("-")
    if len(domain_without_tld) > 24 or entropy > 3.6 or digit_ratio > 0.28 or hyphen_count >= 3:
        weight = 18 if entropy > 3.6 or digit_ratio > 0.28 else 12
        add_threat(
            threats,
            "Random-looking domain",
            "The destination domain has length, entropy, digit, or hyphen patterns seen in disposable phishing hosts.",
            "medium",
            weight,
            f"{domain_without_tld} (entropy {entropy:.2f})",
        )
        score += weight

    spoof_evidence = unicode_spoof_evidence(hostname)
    if spoof_evidence:
        add_threat(
            threats,
            "Unicode spoofing pattern",
            "The domain uses internationalized or lookalike characters that can impersonate a familiar brand.",
            "high",
            22,
            ", ".join(spoof_evidence),
        )
        score += 22

    special_weight = 0
    special_evidence = []
    if "@" in normalized:
        special_weight += 18
        special_evidence.append("@ sign")
    if normalized.count("%") >= 3:
        special_weight += 8
        special_evidence.append("encoded characters")
    if len(host_labels) > 4:
        special_weight += 10
        special_evidence.append("deep subdomains")
    if parsed.path.count("//") or "\\\\" in normalized:
        special_weight += 8
        special_evidence.append("path separator abuse")
    if special_weight:
        add_threat(
            threats,
            "Special character abuse",
            "The URL uses characters or subdomain depth that can disguise the true destination.",
            "high" if special_weight >= 18 else "medium",
            min(28, special_weight),
            ", ".join(special_evidence),
        )
        score += min(28, special_weight)

    query = parse_qs(parsed.query)
    redirect_keys = {"url", "u", "redirect", "redirect_uri", "return", "next", "continue", "dest", "destination"}
    if redirect_keys.intersection(query.keys()):
        add_threat(
            threats,
            "Redirect-heavy query",
            "The URL includes parameters that commonly forward users to another site.",
            "medium",
            10,
            ", ".join(sorted(redirect_keys.intersection(query.keys()))),
        )
        score += 10

    if not threats and parsed.scheme == "https":
        score = 8

    metadata.update(
        {
            "domain_entropy": round(entropy, 3),
            "keyword_hits": keyword_hits,
            "payment_hits": payment_hits,
            "is_shortener": shortener_host in SHORTENERS,
        }
    )

    return build_result(payload, normalized, score, threats, metadata)


def build_result(payload, normalized_url, score, threats, metadata):
    score = clamp(score)
    if score >= 70:
        level = "malicious"
    elif score >= 35:
        level = "warning"
    else:
        level = "safe"

    recommendations = []
    for threat in threats:
        text = recommendation_for(threat["title"])
        if text not in recommendations:
            recommendations.append(text)

    if level == "safe":
        recommendations.extend(
            [
                "Open the destination only in a patched browser.",
                "Confirm the visible domain still matches the expected brand before signing in.",
            ]
        )
    elif level == "warning":
        recommendations.append("Use a sandboxed browser or URL expander before opening the QR destination.")
    else:
        recommendations.append("Block this QR destination and alert the security team.")

    return {
        "payload": payload,
        "normalized_url": normalized_url if normalized_url.startswith(("http://", "https://")) else "",
        "risk_score": score,
        "risk_level": level,
        "threats": threats,
        "recommendations": recommendations[:6],
        "metadata": metadata,
    }
