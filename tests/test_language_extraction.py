"""Tests for language extraction functionality."""


from kards_final_scraper import SHORT_TO_API_CODE, extract_localized_field


def test_extract_localized_field_returns_target_language_api_codes() -> None:
    """Test extracting field in target language with API codes (like from real API)."""
    field_data = {
        "en-EN": "Hello",
        "ru-RU": "Привет",
        "ja-JP": "こんにちは",
    }
    assert extract_localized_field(field_data, "ja") == "こんにちは"


def test_extract_localized_field_returns_target_language_short_codes() -> None:
    """Test extracting field in target language with short codes."""
    field_data = {
        "en": "Hello",
        "ru": "Привет",
        "ja": "こんにちは",
    }
    assert extract_localized_field(field_data, "ja") == "こんにちは"


def test_extract_localized_field_falls_back_to_english_api_codes() -> None:
    """Test fallback to English when target language unavailable (API codes)."""
    field_data = {
        "en-EN": "Hello",
        "ru-RU": "Привет",
    }
    assert extract_localized_field(field_data, "ja") == "Hello"


def test_extract_localized_field_falls_back_to_english_short_codes() -> None:
    """Test fallback to English when target language unavailable (short codes)."""
    field_data = {
        "en": "Hello",
        "ru": "Привет",
    }
    assert extract_localized_field(field_data, "ja") == "Hello"


def test_extract_localized_field_falls_back_to_first_available() -> None:
    """Test fallback to first available language."""
    field_data = {
        "de-DE": "Hallo",
        "fr-FR": "Bonjour",
    }
    result = extract_localized_field(field_data, "ja")
    assert result in ["Hallo", "Bonjour"]


def test_extract_localized_field_handles_non_dict_string() -> None:
    """Test handling of non-dictionary string input."""
    assert extract_localized_field("test", "en") == "test"


def test_extract_localized_field_handles_empty_string() -> None:
    """Test handling of empty string input."""
    assert extract_localized_field("", "en") == ""


def test_extract_localized_field_handles_none() -> None:
    """Test handling of None input."""
    assert extract_localized_field(None, "en") == ""  # type: ignore


def test_extract_localized_field_handles_empty_dict() -> None:
    """Test handling of empty dictionary."""
    assert extract_localized_field({}, "en") == ""


def test_extract_localized_field_handles_number() -> None:
    """Test handling of numeric input."""
    assert extract_localized_field(123, "en") == "123"  # type: ignore


def test_extract_localized_field_russian_available_api_code() -> None:
    """Test Russian language extraction with API code."""
    field_data = {
        "en-EN": "Attack",
        "ru-RU": "Атака",
    }
    assert extract_localized_field(field_data, "ru") == "Атака"


def test_extract_localized_field_all_supported_languages_api_codes() -> None:
    """Test extraction for all supported languages using API codes."""
    from kards_final_scraper import SUPPORTED_LANGUAGES

    # Create field data with API codes (as they come from real API)
    field_data = {SHORT_TO_API_CODE[lang]: f"text_{lang}" for lang in SUPPORTED_LANGUAGES}

    for language in SUPPORTED_LANGUAGES:
        result = extract_localized_field(field_data, language)
        assert result == f"text_{language}"
