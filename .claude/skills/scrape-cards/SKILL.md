---
name: scrape-cards
description: Run KARDS scraper with specified language and format
arguments:
  - name: language
    description: "Language code: en, ru, de, es, fr, it, ja, ko, pl, pt, zh-cn, zh-tw"
    required: true
  - name: format
    description: "Output format: csv, xlsx, json (default: csv)"
    default: csv
  - name: output
    description: "Custom output filename (optional)"
---

# Scrape KARDS Cards

Run the KARDS card scraper to export card data.

## Execution

```bash
uv run python kards_final_scraper.py -l {{language}} -f {{format}}{{#output}} -o {{output}}{{/output}}
```

## Available Languages
- `en` - English
- `ru` - Russian
- `de` - German
- `es` - Spanish
- `fr` - French
- `it` - Italian
- `ja` - Japanese
- `ko` - Korean
- `pl` - Polish
- `pt` - Portuguese
- `zh-cn` - Chinese (Simplified)
- `zh-tw` - Chinese (Traditional)

## Output Formats
- `csv` - Comma-separated values (Excel compatible with BOM)
- `xlsx` - Excel spreadsheet with formatting
- `json` - JSON with metadata
