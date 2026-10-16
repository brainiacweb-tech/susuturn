"""Monetary handling for SusuTurn.

All monetary amounts are validated and converted into integer pesewas
(1 GHS = 100 pesewas) to completely eliminate binary floating-point inaccuracies.
"""

from decimal import Decimal, InvalidOperation
import re
from susuturn.exceptions import InvalidMoneyError

# Regex to strictly validate money format:
# Optional whitespace, optional currency prefix GHS or GH₵, digits, optional . followed by 1 or 2 digits.
# Disallows scientific notation (e.g. 1e5), NaN, Infinity, negative signs.
_MONEY_REGEX = re.compile(r"^(?:GHS|GH₵)?\s*([0-9]+(?:\.[0-9]{1,2})?)$", re.IGNORECASE)


def parse_ghs_to_pesewas(amount_input: str | int | float | Decimal) -> int:
    """Parse a GHS amount into integer pesewas.

    Rules:
    - Must be greater than zero (unless zero is explicitly allowed by specific context; here contributions > 0).
    - Max 2 decimal places allowed.
    - Rejects negative values, invalid text, scientific notation (1e5), NaN, and Infinity.
    - Never uses binary floating-point arithmetic for monetary calculations.
    """
    if amount_input is None:
        raise InvalidMoneyError("Monetary amount cannot be empty.")

    # Convert to string for exact string-based analysis
    # If float was accidentally passed, reject scientific representation or NaN/Inf
    raw_str = str(amount_input).strip()
    if not raw_str:
        raise InvalidMoneyError("Monetary amount cannot be empty.")

    # Explicit check for NaN, Inf, scientific notation
    lower = raw_str.lower()
    if "nan" in lower or "inf" in lower or "e" in lower:
        raise InvalidMoneyError(f"Invalid monetary format '{amount_input}'. Scientific notation, NaN, and Infinity are not allowed.")

    if "-" in raw_str:
        raise InvalidMoneyError(f"Monetary amount must be positive. Received '{amount_input}'.")

    # Match against regex
    match = _MONEY_REGEX.match(raw_str)
    if not match:
        # Check if it was rejected due to excessive decimal places
        if re.search(r"\.[0-9]{3,}", raw_str):
            raise InvalidMoneyError(f"Monetary amount '{amount_input}' has more than 2 decimal places. Silently rounding money is not permitted.")
        raise InvalidMoneyError(f"Invalid monetary amount '{amount_input}'. Expected a valid currency format, e.g. '50.00' or '50'.")

    numeric_str = match.group(1)

    try:
        dec = Decimal(numeric_str)
    except InvalidOperation:
        raise InvalidMoneyError(f"Could not parse monetary amount '{amount_input}'.")

    if dec <= Decimal("0"):
        raise InvalidMoneyError(f"Monetary amount must be greater than zero. Received '{amount_input}'.")

    # Convert to integer pesewas:
    # Split into integer and fractional parts to guarantee exactness
    if "." in numeric_str:
        parts = numeric_str.split(".")
        integer_part = int(parts[0])
        fractional_part = parts[1].ljust(2, "0")
        pesewas = (integer_part * 100) + int(fractional_part)
    else:
        pesewas = int(numeric_str) * 100

    return pesewas


def format_pesewas_to_ghs(pesewas: int, include_prefix: bool = True) -> str:
    """Format integer pesewas into standard Ghana Cedis string representation.

    Example:
        5000 -> "GHS 50.00" (or "50.00" if include_prefix=False)
        2050 -> "GHS 20.50"
        0    -> "GHS 0.00"
    """
    if not isinstance(pesewas, int):
        raise TypeError(f"Pesewas must be an integer, got {type(pesewas).__name__}.")

    is_negative = pesewas < 0
    abs_pesewas = abs(pesewas)
    cedis = abs_pesewas // 100
    rem_pesewas = abs_pesewas % 100

    formatted_num = f"{'-' if is_negative else ''}{cedis}.{rem_pesewas:02d}"
    if include_prefix:
        return f"GHS {formatted_num}"
    return formatted_num
