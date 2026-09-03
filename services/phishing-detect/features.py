"""
Converts a raw URL string into the 111-column feature vector the model expects.
Covers all URL/domain lexical features (character counts, structure, length,
TLD info) purely from the string itself — no network calls, so this stays
fast enough to sit in a request path.

LIMITATION (be upfront about this in your write-up): a handful of the
original dataset's features are network/content-dependent (e.g. whether the
domain is Google-indexed, redirect chains, SSL certificate age). Those are
defaulted to 0 here. This is a known v1 gap — a good "future work" item is
adding an async enrichment step that fills these in from a real HTTP
lookup without blocking the main request.
"""
import re
import json
import os
from urllib.parse import urlparse
import pandas as pd

# Exact column list/order the model was actually trained on (written by train.py)
_FEATURES_PATH = os.path.join(os.path.dirname(__file__), "model_features.json")
with open(_FEATURES_PATH) as f:
    FEATURE_COLUMNS = json.load(f)

SPECIAL_CHARS = {
    "dot": ".", "hyphen": "-", "underline": "_", "slash": "/",
    "questionmark": "?", "equal": "=", "at": "@", "and": "&",
    "exclamation": "!", "space": " ", "tilde": "~", "comma": ",",
    "plus": "+", "asterisk": "*", "hashtag": "#", "dollar": "$",
    "percent": "%",
}

SUSPICIOUS_TLDS = {"tk", "ml", "ga", "cf", "gq", "xyz", "top", "club"}


def _char_counts(text: str, prefix: str) -> dict:
    return {f"qty_{name}_{prefix}": text.count(ch) for name, ch in SPECIAL_CHARS.items()}


def extract_features(url: str) -> dict:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    domain = parsed.netloc
    full_path = parsed.path or ""
    query = parsed.query or ""

    # Split path into directory vs filename the way the dataset does:
    # last path segment with a dot in it = file, everything before = directory
    path_parts = full_path.rsplit("/", 1)
    if len(path_parts) == 2 and "." in path_parts[1]:
        directory, file_part = path_parts[0], path_parts[1]
    else:
        directory, file_part = full_path, ""

    feats = {}
    feats.update(_char_counts(url, "url"))
    feats.update(_char_counts(domain, "domain"))
    feats.update(_char_counts(directory, "directory"))
    feats.update(_char_counts(file_part, "file"))
    feats.update(_char_counts(query, "params") if query else {f"qty_{n}_params": 0 for n in SPECIAL_CHARS})

    tld = domain.split(".")[-1].lower() if "." in domain else ""

    feats["qty_tld_url"] = len(tld)
    feats["length_url"] = len(url)
    feats["qty_dot_domain"] = domain.count(".")
    feats["domain_length"] = len(domain)
    feats["directory_length"] = len(directory)
    feats["file_length"] = len(file_part)
    feats["params_length"] = len(query)
    feats["qty_vowels_domain"] = sum(domain.lower().count(v) for v in "aeiou")
    feats["domain_in_ip"] = int(bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain)))
    feats["server_client_domain"] = int("server" in domain.lower() or "client" in domain.lower())
    feats["tld_present_params"] = int(bool(query))
    feats["qty_params"] = len(query.split("&")) if query else 0
    feats["email_in_url"] = int(bool(re.search(r"[\w.-]+@[\w.-]+", url)))
    feats["url_shortened"] = int(any(s in domain for s in
                                      ["bit.ly", "tinyurl", "t.co", "goo.gl", "ow.ly"]))

    # Any remaining columns (rare edge-case ones) default to 0
    for col in FEATURE_COLUMNS:
        if col not in feats:
            feats[col] = 0

    # Return in the exact training column order
    return {col: feats.get(col, 0) for col in FEATURE_COLUMNS}


def url_to_dataframe(url: str) -> pd.DataFrame:
    return pd.DataFrame([extract_features(url)])
