import base64
import json


def _rot13(text: str) -> str:
    """Apply ROT13 cipher (letters only)."""
    out = []
    for ch in text:
        o = ord(ch)
        if 65 <= o <= 90:
            out.append(chr(((o - 65 + 13) % 26) + 65))
        elif 97 <= o <= 122:
            out.append(chr(((o - 97 + 13) % 26) + 97))
        else:
            out.append(ch)
    return ''.join(out)


def _replace_patterns(txt: str) -> str:
    """Strip marker substrings used as obfuscation separators."""
    for pat in ['@$', '^^', '~@', '%?', '*~', '!!', '#&']:
        txt = txt.replace(pat, '')
    return txt


def _shift_chars(text: str, shift: int) -> str:
    """Shift character code-points by *-shift* (decode)."""
    return ''.join(chr(ord(c) - shift) for c in text)


def _safe_b64_decode(s: str) -> str:
    """Base64 decode with safe padding and utf-8 fallback."""
    pad = len(s) % 4
    if pad:
        s += '=' * (4 - pad)
    return base64.b64decode(s).decode('utf-8', errors='replace')


def deobfuscate_embedded_json(raw_json: str):
    """Return a dict or str extracted from the obfuscated JSON array found in <script type="application/json">."""
    try:
        arr = json.loads(raw_json)
        if not (isinstance(arr, list) and arr and isinstance(arr[0], str)):
            return None
        obf = arr[0]
    except json.JSONDecodeError:
        return None

    try:
        step1 = _rot13(obf)
        step2 = _replace_patterns(step1)
        step3 = _safe_b64_decode(step2)
        step4 = _shift_chars(step3, 3)
        step5 = step4[::-1]
        step6 = _safe_b64_decode(step5)
        try:
            return json.loads(step6)  # ideally a dict with direct_access_url / source
        except json.JSONDecodeError:
            return step6  # return plain string for fallback regex search
    except Exception:
        return None


# Function to clean and pad base64 safely
def clean_base64(s):
    try:
        s = s.replace('\\', '')  # remove literal backslashes
        missing_padding = len(s) % 4
        if missing_padding:
            s += '=' * (4 - missing_padding)
        # Validate if the string is valid base64
        base64.b64decode(s, validate=True)
        return s
    except (base64.binascii.Error, ValueError) as e:
        print(f"[!] Invalid base64 string: {e}")
        return None
