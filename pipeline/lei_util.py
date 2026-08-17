"""LEI syntactic validation per ISO 17442: 20 chars, [A-Z0-9], chars 5-6 reserved
"00" in pre-2017 scheme (not enforced), ISO 7064 MOD 97-10 check digits."""
import re

LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")


def mod97(numeric: str) -> int:
    rem = 0
    for ch in numeric:
        rem = (rem * 10 + int(ch)) % 97
    return rem


def lei_checksum_ok(lei: str) -> bool:
    numeric = "".join(str(int(c, 36)) for c in lei)
    return mod97(numeric) == 1


def classify_lei(raw):
    """Return (bucket, normalised) where bucket is one of:
    empty | placeholder | malformed | bad_checksum | valid"""
    if raw is None:
        return "empty", None
    s = str(raw).strip()
    if s == "" or s.upper() in {"N/A", "NA", "NONE", "NULL"}:
        return "empty", None
    up = s.upper()
    if len(set(up)) == 1 and len(up) == 20:  # e.g. all zeros
        return "placeholder", up
    if not LEI_RE.match(up):
        return "malformed", up
    if not lei_checksum_ok(up):
        return "bad_checksum", up
    return "valid", up


ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
CUSIP_RE = re.compile(r"^[0-9A-Z@#*]{8}[0-9]$")


def isin_checksum_ok(isin: str) -> bool:
    digits = "".join(str(int(c, 36)) for c in isin)
    total, dbl = 0, len(digits) % 2 == 0
    for i, ch in enumerate(digits):
        d = int(ch)
        if (i % 2 == 0) == dbl:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def cusip_checksum_ok(cusip: str) -> bool:
    total = 0
    for i, ch in enumerate(cusip[:8]):
        if ch.isdigit():
            v = int(ch)
        elif ch.isalpha():
            v = ord(ch) - 55
        else:
            v = {"*": 36, "@": 37, "#": 38}[ch]
        if i % 2 == 1:
            v *= 2
        total += v // 10 + v % 10
    return (10 - total % 10) % 10 == int(cusip[8])


def classify_isin(raw):
    if raw is None:
        return "empty", None
    s = str(raw).strip().upper()
    if s in {"", "N/A", "NA", "NONE", "NULL", "000000000000"}:
        return "empty", None
    if not ISIN_RE.match(s):
        return "malformed", s
    if not isin_checksum_ok(s):
        return "bad_checksum", s
    return "valid", s


def classify_cusip(raw):
    if raw is None:
        return "empty", None
    s = str(raw).strip().upper()
    if s in {"", "N/A", "NA", "NONE", "NULL", "000000000", "0"*9}:
        return "empty", None
    if not CUSIP_RE.match(s):
        return "malformed", s
    if not cusip_checksum_ok(s):
        return "bad_checksum", s
    return "valid", s
