"""Tests for CLI interface and class initialization."""

import pytest

from kards_final_scraper import SUPPORTED_FORMATS, SUPPORTED_LANGUAGES, KardsFinalScraper


def test_scraper_init_default_parameters() -> None:
    """Test scraper initialization with default parameters."""
    scraper = KardsFinalScraper()

    assert scraper.language == "ru"
    assert scraper.export_format == "csv"
    assert scraper.output_file is None


def test_scraper_init_custom_language() -> None:
    """Test scraper initialization with custom language."""
    scraper = KardsFinalScraper(language="en")

    assert scraper.language == "en"
    assert scraper.export_format == "csv"


def test_scraper_init_custom_format() -> None:
    """Test scraper initialization with custom format."""
    scraper = KardsFinalScraper(export_format="xlsx")

    assert scraper.language == "ru"
    assert scraper.export_format == "xlsx"


def test_scraper_init_custom_output() -> None:
    """Test scraper initialization with custom output filename."""
    scraper = KardsFinalScraper(output_file="custom.xlsx")

    assert scraper.output_file == "custom.xlsx"


def test_scraper_init_all_parameters() -> None:
    """Test scraper initialization with all parameters."""
    scraper = KardsFinalScraper(
        language="ja",
        export_format="csv",
        output_file="japanese.csv"
    )

    assert scraper.language == "ja"
    assert scraper.export_format == "csv"
    assert scraper.output_file == "japanese.csv"


def test_scraper_init_invalid_language() -> None:
    """Test scraper initialization with invalid language."""
    with pytest.raises(ValueError, match="Unsupported language"):
        KardsFinalScraper(language="invalid")


def test_scraper_init_invalid_format() -> None:
    """Test scraper initialization with invalid format."""
    with pytest.raises(ValueError, match="Unsupported format"):
        KardsFinalScraper(export_format="pdf")


def test_scraper_init_all_supported_languages() -> None:
    """Test scraper can be initialized with any supported language."""
    for language in SUPPORTED_LANGUAGES:
        scraper = KardsFinalScraper(language=language)
        assert scraper.language == language


def test_scraper_init_all_supported_formats() -> None:
    """Test scraper can be initialized with any supported format."""
    for fmt in SUPPORTED_FORMATS:
        scraper = KardsFinalScraper(export_format=fmt)
        assert scraper.export_format == fmt


def test_scraper_generate_filename_default() -> None:
    """Test filename generation with default parameters."""
    scraper = KardsFinalScraper()
    filename = scraper._generate_filename()

    assert filename == "kards_collection_ru.csv"


def test_scraper_generate_filename_english() -> None:
    """Test filename generation for English."""
    scraper = KardsFinalScraper(language="en", export_format="csv")
    filename = scraper._generate_filename()

    assert filename == "kards_collection_en.csv"


def test_scraper_generate_filename_japanese() -> None:
    """Test filename generation for Japanese."""
    scraper = KardsFinalScraper(language="ja", export_format="json")
    filename = scraper._generate_filename()

    assert filename == "kards_collection_ja.json"


def test_scraper_generate_filename_chinese_simplified() -> None:
    """Test filename generation for Chinese Simplified."""
    scraper = KardsFinalScraper(language="zh-cn", export_format="xlsx")
    filename = scraper._generate_filename()

    assert filename == "kards_collection_zh-cn.xlsx"


def test_scraper_generate_filename_chinese_traditional() -> None:
    """Test filename generation for Chinese Traditional."""
    scraper = KardsFinalScraper(language="zh-tw", export_format="xlsx")
    filename = scraper._generate_filename()

    assert filename == "kards_collection_zh-tw.xlsx"


def test_scraper_cards_initialized_empty() -> None:
    """Test that cards list is initialized empty."""
    scraper = KardsFinalScraper()

    assert scraper.cards == []
    assert len(scraper.card_ids) == 0
    assert scraper.api_data == []
