# KARDS GraphQL Schema

Endpoint: `https://api.kards.com/graphql`

Generated: 2026-04-29

Do not edit by hand. Regenerate with:

```
uv run python experiments/fast-fetch/introspect.py
uv run python experiments/fast-fetch/render_schema_md.py
```

## Notable for kardscm -- localization

Schema introspection is **disabled** on the production Apollo server:

```
HTTP 400: {"errors":[{"message":"GraphQL introspection is not allowed by Apollo Server, but the query contained __schema or __type. To enable introspection, pass introspection: true to ApolloServer in production","locations":[{"line":1,"column":3}],"extensions":{"code":"GRAPHQL_VALIDATION_FAILED"}}]}

```

### Bundle probe findings (Phase 1, Task C)

`experiments/fast-fetch/bundle_probe.py` was run against
`https://www.kards.com/en/decks/collection`. Captured 152 network requests;
no standalone `i18n`, `locale`, `lang`, `translation`, or `messages` JSON
bundle was served. The only suspicious URLs were Next.js route chunks whose
*paths* contain the `[locale]` directory placeholder (e.g.
`/_next/static/chunks/app/(decks)/%5Blocale%5D/decks/collection/page-*.js`).
Those are JavaScript route bundles, not translation files.

This means the KARDS web client almost certainly inlines its translated
strings inside the route JS chunks (typical Next.js / `next-intl` pattern
when `output: 'export'` or per-route messages are embedded at build time).
There is no plain JSON locale bundle to download.

### Confirmed localization signal

The existing `getCards` GraphQL query (see `kardscm/constants.py`) takes
`language: String` and each card node returns a `json` blob whose
`title.<locale>` / `text.<locale>` keys carry per-card localized text
(`en-EN` / `ru-RU`, matching `LanguageConfig.locale_key`). Card image URLs
also include the locale segment, e.g.
`/images/card/v48/en-EN/<slug>.avif`. **Per-card text is therefore covered
by the API.** What the API does *not* expose is the localized labels for
*metadata* categories below.

### Coverage per kardscm category

- **factions**: API does NOT expose localized labels -- `cards` accepts a `language` arg but faction labels are hardcoded in `LanguageConfig.faction_names`. Likely needs JS-bundle scraping or a manual translation table.
- **types**: API does NOT expose localized labels -- card type strings (`unit`, `order`, `countermeasure`) are filter values, not localized in the response. Hardcoded in `LanguageConfig.type_names`.
- **rarities**: API does NOT expose localized labels -- rarity strings (`Standard`, `Limited`, `Special`, `Elite`) are filter values. Hardcoded in `LanguageConfig.rarity_names`.
- **sets**: API does NOT expose localized labels -- set codes are filter values. Hardcoded in `LanguageConfig.set_names`.
- **abilities**: API does NOT expose localized labels -- abilities ride along inside the per-card `json.attributes` field as code strings (e.g. `Blitz`, `Ambush`). The card-text translation in `json.text.<locale>` describes the ability inside prose, but the *attribute key* itself is not translated. Hardcoded in `LanguageConfig.ability_names`.
- **nation_display_names**: API does NOT expose localized labels -- nation/faction display strings are not returned by `cards`. Hardcoded in `LanguageConfig.deck_nation_to_db` (mapping only) and `faction_names` (display).

### Next steps

1. Treat the six categories above as "static maps owned by kardscm" -- do not
   plan an API-driven refactor for them.
2. Optional follow-up: download one Russian-locale Next.js route chunk
   (e.g. `/_next/static/chunks/app/(decks)/%5Blocale%5D/decks/collection/page-*.js`),
   grep for known faction strings in Russian; if the chunk inlines them,
   harvest a translation table for free. Otherwise: keep the manual
   `LanguageConfig` strategy and just expand it for new locales.
3. For Phase 2 (ability filters): the `cards` query has no `ability` /
   `attribute` argument, so filtering remains a client-side operation
   over `json.attributes` from each card row.

## Notable for kardscm -- ability filters

Not enumerable without introspection. The only confirmed filter surface is
the `cards` query in `kardscm/constants.py`, which accepts:

- `nationIds: [Int]`
- `kredits: [Int]`
- `q: String`
- `type: [String]`
- `rarity: [String]`
- `set: [String]`
- `showSpawnables`, `showExiles`, `showReserved`: `Boolean`

There is no `ability` / `attribute` / `keyword` argument on `cards` in the
known query template, so ability filtering is currently a client-side
concern.

## Root operations / Object types / Input objects / Enums / Scalars / Interfaces

Unavailable -- see the introspection-blocked notice above.
