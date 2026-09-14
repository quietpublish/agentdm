def to_roman(n: int) -> str:
    """1..3999 -> Roman numeral (subtractive forms: IV, IX, XL, XC, CD, CM). Raise ValueError outside the range."""
    raise NotImplementedError


def from_roman(s: str) -> int:
    """Inverse of to_roman. Raise ValueError on invalid or non-canonical input such as 'IIII' or 'VX'."""
    raise NotImplementedError
