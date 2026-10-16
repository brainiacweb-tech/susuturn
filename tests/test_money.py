"""Unit tests for exact monetary parsing and formatting."""

import pytest
from susuturn.exceptions import InvalidMoneyError
from susuturn.money import parse_ghs_to_pesewas, format_pesewas_to_ghs


class TestMoneyParsing:
    """Tests covering GHS parsing into integer pesewas."""

    def test_valid_integer_amount(self):
        assert parse_ghs_to_pesewas("50") == 5000
        assert parse_ghs_to_pesewas("1") == 100
        assert parse_ghs_to_pesewas(50) == 5000

    def test_valid_decimal_amount(self):
        assert parse_ghs_to_pesewas("50.00") == 5000
        assert parse_ghs_to_pesewas("20.50") == 2050
        assert parse_ghs_to_pesewas("0.05") == 5
        assert parse_ghs_to_pesewas("0.5") == 50

    def test_currency_prefix_and_whitespace(self):
        assert parse_ghs_to_pesewas("GHS 50.00") == 5000
        assert parse_ghs_to_pesewas("ghs  20.50 ") == 2050
        assert parse_ghs_to_pesewas("GH₵ 100.25") == 10025

    def test_reject_zero_amount(self):
        with pytest.raises(InvalidMoneyError, match="greater than zero"):
            parse_ghs_to_pesewas("0")
        with pytest.raises(InvalidMoneyError, match="greater than zero"):
            parse_ghs_to_pesewas("0.00")

    def test_reject_negative_amount(self):
        with pytest.raises(InvalidMoneyError, match="positive"):
            parse_ghs_to_pesewas("-50.00")
        with pytest.raises(InvalidMoneyError, match="positive"):
            parse_ghs_to_pesewas("-0.50")

    def test_reject_more_than_two_decimal_places(self):
        with pytest.raises(InvalidMoneyError, match="more than 2 decimal places"):
            parse_ghs_to_pesewas("50.123")
        with pytest.raises(InvalidMoneyError, match="more than 2 decimal places"):
            parse_ghs_to_pesewas("10.999")

    def test_reject_scientific_notation(self):
        with pytest.raises(InvalidMoneyError, match="Scientific notation"):
            parse_ghs_to_pesewas("1e2")
        with pytest.raises(InvalidMoneyError, match="Scientific notation"):
            parse_ghs_to_pesewas("5E1")

    def test_reject_nan_and_infinity(self):
        with pytest.raises(InvalidMoneyError, match="NaN"):
            parse_ghs_to_pesewas("NaN")
        with pytest.raises(InvalidMoneyError, match="Infinity"):
            parse_ghs_to_pesewas("Infinity")
        with pytest.raises(InvalidMoneyError, match="Infinity"):
            parse_ghs_to_pesewas("-inf")

    def test_reject_empty_or_invalid_string(self):
        with pytest.raises(InvalidMoneyError, match="cannot be empty"):
            parse_ghs_to_pesewas("")
        with pytest.raises(InvalidMoneyError, match="cannot be empty"):
            parse_ghs_to_pesewas("   ")
        with pytest.raises(InvalidMoneyError, match="Invalid monetary amount"):
            parse_ghs_to_pesewas("abc")


class TestMoneyFormatting:
    """Tests covering formatting pesewas to standard GHS strings."""

    def test_format_standard_pesewas(self):
        assert format_pesewas_to_ghs(5000) == "GHS 50.00"
        assert format_pesewas_to_ghs(2050) == "GHS 20.50"
        assert format_pesewas_to_ghs(15000) == "GHS 150.00"
        assert format_pesewas_to_ghs(5) == "GHS 0.05"
        assert format_pesewas_to_ghs(0) == "GHS 0.00"

    def test_format_without_prefix(self):
        assert format_pesewas_to_ghs(5000, include_prefix=False) == "50.00"
        assert format_pesewas_to_ghs(2050, include_prefix=False) == "20.50"

    def test_format_negative(self):
        assert format_pesewas_to_ghs(-500) == "GHS -5.00"

    def test_format_type_error(self):
        with pytest.raises(TypeError, match="must be an integer"):
            format_pesewas_to_ghs(50.0)  # type: ignore
