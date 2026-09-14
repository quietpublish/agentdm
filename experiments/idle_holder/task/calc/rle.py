def encode(s: str) -> str:
    """Run-length encode: 'aaabcc' -> '3a1b2c'. Empty -> ''. Digits in input are not allowed: raise ValueError."""
    raise NotImplementedError


def decode(s: str) -> str:
    """Inverse of encode; counts may be multi-digit ('12a'). Raise ValueError on malformed input."""
    raise NotImplementedError
