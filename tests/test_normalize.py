"""Unit tests for the pure normalizers. Each must drop (never invent) on bad input."""

from __future__ import annotations

from transformer.normalize import (
    canonicalize_skill,
    normalize_country,
    normalize_email,
    normalize_month,
    normalize_name,
    normalize_phone,
)


class TestPhones:
    def test_e164_with_country_code(self):
        assert normalize_phone("+1 (415) 555-2671").value == "+14155552671"

    def test_region_hint_for_bare_number(self):
        assert normalize_phone("(415) 555-2671", "US").value == "+14155552671"

    def test_garbage_dropped(self):
        assert normalize_phone("not a phone").value is None

    def test_no_region_no_country_code_dropped(self):
        # No country code and no region hint -> we refuse to guess a country.
        assert normalize_phone("415 555 2671").value is None


class TestDates:
    def test_iso_month(self):
        assert normalize_month("2021-03").value == "2021-03"

    def test_month_name(self):
        assert normalize_month("March 2021").value == "2021-03"

    def test_slash_month_year(self):
        assert normalize_month("03/2021").value == "2021-03"

    def test_present_is_none(self):
        assert normalize_month("Present").value is None

    def test_year_only_dropped(self):
        # We will not invent a month, so a bare year does not become YYYY-01.
        assert normalize_month("2019").value is None


class TestCountry:
    def test_alias(self):
        assert normalize_country("USA").value == "US"

    def test_alpha2_passthrough(self):
        assert normalize_country("DE").value == "DE"

    def test_fuzzy_flagged(self):
        res = normalize_country("The Netherlands")
        assert res.value == "NL" and res.fuzzy is True

    def test_unknown_dropped(self):
        assert normalize_country("Atlantis").value is None


class TestEmail:
    def test_lowercased_trimmed(self):
        assert normalize_email("  John.Doe@Example.COM ").value == "john.doe@example.com"

    def test_invalid_dropped(self):
        assert normalize_email("nope").value is None


class TestSkills:
    def test_alias_to_canonical(self):
        assert canonicalize_skill("JS").value == "JavaScript"

    def test_unknown_kept_titlecased(self):
        assert canonicalize_skill("kafka").value == "Kafka"

    def test_acronym_preserved(self):
        assert canonicalize_skill("CSS").value == "CSS"


class TestName:
    def test_all_caps_recased(self):
        assert normalize_name("JOHN DOE").value == "John Doe"

    def test_mixed_case_preserved(self):
        assert normalize_name("  Jane   McDonald ").value == "Jane McDonald"
