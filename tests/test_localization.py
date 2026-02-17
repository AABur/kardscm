"""Tests for kardscm.scraping.localization."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kardscm.config import LANGUAGE_EN, LANGUAGE_RU
from kardscm.scraping.localization import (
    _parse_translations,
    decode_escapes,
    extract_localized_field,
    load_translations,
    translate_value,
)


@pytest.mark.parametrize(
    ("input_text", "expected"),
    [
        (r"\u0041", "A"),
        (r"\xab", "\xab"),
        (r"\n", "\n"),
        (r"\t", "\t"),
        ("\\\\", "\\"),
        ("", ""),
        ("plain text", "plain text"),
        (r"\xabtext\xbb", "\xabtext\xbb"),
    ],
    ids=["unicode_u", "hex", "newline", "tab", "backslash", "empty", "no_escapes", "mixed"],
)
def test_decode_escapes(input_text, expected):
    assert decode_escapes(input_text) == expected


class TestExtractLocalizedField:
    def test_configured_lang_ru(self):
        data = {"ru": "Танк", "en": "Tank"}
        result = extract_localized_field(data, LANGUAGE_RU)
        assert result == "Танк"

    def test_configured_lang_en(self):
        data = {"en": "Tank", "ru": "Танк"}
        result = extract_localized_field(data, LANGUAGE_EN)
        assert result == "Tank"

    def test_english_fallback(self):
        data = {"en": "Tank", "de": "Panzer"}
        result = extract_localized_field(data, LANGUAGE_RU)
        assert result == "Tank"

    def test_string_input(self):
        result = extract_localized_field("direct string", LANGUAGE_EN)
        assert result == "direct string"

    def test_empty_dict(self):
        result = extract_localized_field({}, LANGUAGE_EN)
        assert result == ""

    def test_none_input(self):
        result = extract_localized_field(None, LANGUAGE_EN)
        assert result == ""

    def test_empty_string_input(self):
        result = extract_localized_field("", LANGUAGE_EN)
        assert result == ""


class TestTranslateValue:
    def test_found(self):
        translations = {"TJBHlP": "Стандартная"}
        result = translate_value("rarity", "Standard", translations)
        assert result == "Стандартная"

    def test_case_insensitive(self):
        translations = {"TJBHlP": "Стандартная"}
        result = translate_value("rarity", "standard", translations)
        assert result == "Стандартная"

    def test_not_found(self):
        result = translate_value("rarity", "Mythic", {})
        assert result == "Mythic"

    def test_empty_value(self):
        result = translate_value("rarity", "", {})
        assert result == ""

    def test_unknown_category(self):
        result = translate_value("unknown_cat", "SomeValue", {})
        assert result == "SomeValue"

    def test_whitespace_stripped(self):
        translations = {"TJBHlP": "Стандартная"}
        result = translate_value("rarity", " Standard ", translations)
        assert result == "Стандартная"

    def test_translation_id_not_in_translations(self):
        result = translate_value("rarity", "Standard", {})
        assert result == "Standard"


class TestParseTranslations:
    def test_extracts_known_ids(self):
        # Build JS content with known translation IDs for "rarity" mappings
        # KNOWN_MAPPINGS["rarity"] = {"Standard": "TJBHlP", "Limited": "HhURN3", ...}
        js = (
            '"TJBHlP":"Standard","TJBHlP":"Стандартная",'
            '"HhURN3":"Limited","HhURN3":"Лимитированная",'
        )
        result = _parse_translations(js, lang_index=1)
        assert result["TJBHlP"] == "Стандартная"
        assert result["HhURN3"] == "Лимитированная"

    def test_lang_index_0(self):
        js = '"TJBHlP":"Standard","TJBHlP":"Стандартная"'
        result = _parse_translations(js, lang_index=0)
        assert result["TJBHlP"] == "Standard"

    def test_fallback_to_last_match(self):
        # If lang_index exceeds number of matches, use last match
        js = '"TJBHlP":"OnlyOne"'
        result = _parse_translations(js, lang_index=5)
        assert result["TJBHlP"] == "OnlyOne"

    def test_no_matches(self):
        js = "no relevant content here"
        result = _parse_translations(js, lang_index=0)
        assert result == {}

    def test_empty_content(self):
        result = _parse_translations("", lang_index=0)
        assert result == {}


class TestLoadTranslations:
    @pytest.mark.asyncio
    async def test_success(self):
        html = '<script src="/_next/static/chunks/2840-abc.js"></script>'
        js_content = '"TJBHlP":"Standard","TJBHlP":"Стандартная"'

        mock_html_response = MagicMock()
        mock_html_response.text = html
        mock_js_response = MagicMock()
        mock_js_response.text = js_content

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_html_response, mock_js_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("kardscm.scraping.localization.httpx.AsyncClient", return_value=mock_client):
            result = await load_translations(LANGUAGE_RU)

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_no_js_file_found(self):
        html = '<script src="/_next/static/chunks/other-file.js"></script>'

        mock_response = MagicMock()
        mock_response.text = html

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("kardscm.scraping.localization.httpx.AsyncClient", return_value=mock_client):
            result = await load_translations(LANGUAGE_EN)

        assert result == {}

    @pytest.mark.asyncio
    async def test_network_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("kardscm.scraping.localization.httpx.AsyncClient", return_value=mock_client):
            result = await load_translations(LANGUAGE_EN)

        assert result == {}
