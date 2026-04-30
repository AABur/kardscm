# Video-first LLM Deck Testing Protocol

**Status:** ready for manual experiment
**Date:** 2026-05-01
**Scope:** private project, outside public `kardscm`

## Goal

Test whether current multimodal LLMs can use KARDS gameplay videos to produce
useful deck corrections and deck-building advice.

This is an experiment, not an implementation plan. The output should tell us:

- whether models can understand real KARDS gameplay from screen recordings;
- how often they hallucinate cards, effects, rules, and opponent actions;
- whether supplying the current card catalog materially improves advice;
- whether supplying the exact deck list materially improves advice;
- whether player notes improve accuracy enough to justify a hybrid workflow;
- whether a video-first pipeline is worth building later.

## Core Assumption

The model does not know the current KARDS card pool reliably. Every test run
must therefore include an up-to-date full catalog of cards that exist in the
game, exported from `kardscm`.

This is not the player's owned collection. It is the full real card catalog
known to the current `kardscm sync`.

Recommended export:

```bash
uv run kardscm sync --yes
uv run kardscm export -f json -o artifacts/card-catalog-current.json
```

If a model recommends a card absent from `card-catalog-current.json`, count it
as a hallucination unless the absence is explained by an export or sync error.

## Inputs Per Match

Each tested match should have one folder:

```text
experiments/
  match_001/
    video.mp4
    deck.txt
    metadata.md
    card-catalog-current.json
    runs/
      gpt_run_1.md
      gpt_run_2.md
      gpt_run_3.md
      gemini_run_1.md
      reviewer_gemini_on_gpt_run_1.md
    evaluation.md
```

`video.mp4` is the original gameplay recording:

- format: MP4
- codec: H.264
- resolution: 2340x1080
- frame rate: about 33 fps
- client language: Russian

`deck.txt` is the exact deck used in the match, preferably exported from the
KARDS client or from `kardscm deck export`.

`metadata.md` should be short and factual:

```markdown
# Match 001

- deck_name:
- result: win | loss | unknown
- known_opponent_nation:
- known_opponent_archetype:
- game_mode:
- recording_notes:
- user_note:
```

`user_note` is optional. Keep it to 2-5 sentences when used. It should capture
what the player noticed, not a full match report.

## Match Selection

Start with 3-5 matches:

1. A win where the deck worked as intended.
2. A loss against fast pressure.
3. A long control or value game.
4. A match with an obvious piloting mistake.
5. A match where the suspected issue is deck construction, not play.

Do not start with 20 videos. The first goal is to measure signal quality, not
build a dataset.

## Test Modes

Run the same match in several modes. The card catalog is included in every
mode.

### Mode A: Video + Card Catalog

Inputs:

- `video.mp4`
- `card-catalog-current.json`

Purpose:

Checks whether the model can understand the match when it has the real card
pool but not the exact deck list. This should expose whether it can infer
played cards and archetypes from video.

Expected weakness:

The model may guess missing deck contents. Those guesses must be treated as
low confidence.

### Mode B: Video + Card Catalog + Deck List

Inputs:

- `video.mp4`
- `card-catalog-current.json`
- `deck.txt`

Purpose:

Main useful mode. The model sees what cards exist and what cards were actually
available in the deck. Recommendations should be constrained by the real card
catalog and grounded in the deck list.

Expected strength:

The model should stop inventing impossible cards and should make more concrete
replacement suggestions.

### Mode C: Video + Card Catalog + Deck List + Player Note

Inputs:

- `video.mp4`
- `card-catalog-current.json`
- `deck.txt`
- `metadata.md` with `user_note`

Purpose:

Tests the hybrid approach. The model gets the player's own observations in
addition to the video.

Expected strength:

This should produce the best practical recommendations if the video is hard to
read or the model misses important board-state context.

## Repeated Runs

For each model and each mode, run the prompt at least three times:

```text
match_001_gpt_mode_b_run_1.md
match_001_gpt_mode_b_run_2.md
match_001_gpt_mode_b_run_3.md
```

The goal is to measure stability. If the model recommends different cuts and
adds on every run, it has not extracted a stable signal from the video.

Use the same prompt text for repeated runs. Do not tune the prompt between run
1 and run 3 for the same model/mode combination.

## Advisor Prompt

Use this prompt for the primary model that watches the video.

```text
Ты анализируешь запись партии KARDS. Твоя задача - помочь скорректировать деку,
а не пересказывать матч.

Входные данные:
- видео партии;
- актуальный полный каталог карт, которые существуют в игре;
- возможно, точный список моей деки;
- возможно, короткая заметка игрока после партии.

Важные правила:
1. Используй только карты из приложенного каталога карт.
2. Если точный список деки приложен, считай его источником истины о моей деке.
3. Не выдумывай карты, эффекты, правила, архетипы или действия противника.
4. Если ты не уверен, прямо пиши "не уверен".
5. Отделяй факты, видимые на видео, от гипотез.
6. Отделяй проблемы пилотирования от проблем deck building.
7. Не предлагай замену карты, если не можешь объяснить, какую проблему она решает.

Ответ дай в такой структуре:

1. Что удалось надежно определить из видео
- результат партии;
- примерный архетип противника;
- ключевые угрозы противника;
- карты моей деки, которые реально повлияли на игру;
- карты моей деки, которые выглядели слабо, поздно или неуместно.

2. Где анализ ненадежен
- какие моменты видео плохо читаются;
- какие карты или действия ты не смог уверенно распознать;
- какие выводы являются гипотезами, а не фактами.

3. Диагноз по деке
- 3-5 главных проблем деки в этой партии;
- какие проблемы связаны с пилотированием;
- какие проблемы связаны с составом деки.

4. Рекомендации
- предложи до 5 замен карт;
- для каждой замены укажи: убрать X, добавить Y, причина, какую проблему это решает;
- используй только карты из приложенного каталога;
- если данных недостаточно для замены, скажи это вместо выдумывания.

5. Проверяемые утверждения
В конце выпиши список утверждений, которые пользователь должен проверить вручную
по видео.
```

## Reviewer Prompt

Use this prompt for a second model that reviews an advisor response. At the
first review level, the reviewer does not watch the video.

Inputs:

- `card-catalog-current.json`
- `deck.txt`, if available in the tested mode
- advisor response
- user's manual evaluation, if already written
- optional confirmed facts from `metadata.md`

Prompt:

```text
Ты проверяешь качество анализа KARDS-деки. Не делай вид, что видел видео.
У тебя есть только каталог реальных карт, список деки, ответ другой модели и,
возможно, ручная оценка пользователя.

Твоя задача:
1. Найти утверждения, которые не подтверждены входными данными.
2. Найти возможные галлюцинации: несуществующие карты, неверные эффекты,
   неподтвержденные архетипы, неподтвержденные действия противника.
3. Проверить, входят ли все предложенные карты в приложенный каталог.
4. Проверить, логичны ли предложенные замены относительно заявленных проблем.
5. Отделить полезные рекомендации от слабых.
6. Сформулировать финальный список советов, которые стоит оставить пользователю.

Не добавляй новые карты, факты или события, если они не следуют из входных
данных.
```

## Human Evaluation Rubric

Create `evaluation.md` for each match:

```markdown
# Evaluation: Match 001

## Runs

| Run | Mode | Model | Video understanding | Card recognition | Opponent read | Deck diagnosis | Recommendations | Hallucinations | Usable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gpt_b_1 | B | GPT | 0-2 | 0-2 | 0-2 | 0-2 | 0-2 | 0-2 | yes/no |

## Scale

- 0 = bad
- 1 = mixed
- 2 = good

## Notes Per Run

### gpt_b_1

- best_suggestion:
- worst_error:
- hallucinated_cards:
- unsupported_claims:
- notes:
```

For `Hallucinations`, use:

- `0`: many hallucinations or a critical fabricated premise;
- `1`: some hallucinations, but the answer is partially usable;
- `2`: no important hallucinations.

## Success Criteria

Continue developing a video-first pipeline only if the first 3-5 matches show
at least this:

- Mode B or C reliably beats Mode A.
- The model usually identifies the result and broad opponent plan.
- The model rarely recommends cards outside `card-catalog-current.json`.
- At least 30-50% of recommendations are judged usable by the player.
- Repeated runs produce similar diagnosis, even if suggested replacements vary.
- Reviewer model catches some hallucinations or weak reasoning without watching
  the video.

If these criteria are not met, switch to a hybrid workflow:

- video stays attached as evidence;
- player writes short match notes;
- LLM analyzes `card catalog + deck list + match journal`;
- video OCR/CV automation is deferred.

## What To Compare

After the first batch, compare:

1. Mode A vs Mode B: does the deck list prevent bad guesses?
2. Mode B vs Mode C: do player notes materially improve recommendations?
3. Run 1 vs Run 2 vs Run 3: is the diagnosis stable?
4. Advisor vs reviewer: does second-model review catch useful issues?
5. Model family vs model family: which model is best at video understanding,
   and which is best at critique?

## Practical Workflow

1. Sync the current catalog.

   ```bash
   uv run kardscm sync --yes
   ```

2. Export the current full card catalog.

   ```bash
   mkdir -p artifacts
   uv run kardscm export -f json -o artifacts/card-catalog-current.json
   ```

3. Create one folder per match.

   ```text
   experiments/match_001/
   ```

4. Copy in:

   - `video.mp4`
   - `deck.txt`
   - `card-catalog-current.json`
   - `metadata.md`

5. Run Mode A three times in one model.

6. Run Mode B three times in the same model.

7. Run Mode C three times if you have a useful player note.

8. Repeat on another model only after the first model's runs are saved.

9. Fill `evaluation.md` manually.

10. Send selected advisor responses to a reviewer model using the reviewer
    prompt.

11. After 3-5 matches, write a short batch summary:

    ```markdown
    # Batch 001 Summary

    - matches_tested:
    - best_mode:
    - best_model:
    - common_hallucinations:
    - useful_recommendation_rate:
    - should_continue_video_first: yes/no
    - next_changes_to_prompt:
    ```

## Non-goals

- No automatic OCR pipeline yet.
- No automatic frame extraction yet.
- No private app UI yet.
- No attempt to train or fine-tune a model.
- No public repository changes beyond this planning document.

## Next Step After Experiment

If the experiment succeeds, the next design should be for a private
`kards-llm-lab` project that can:

- store match folders;
- copy/export the current `kardscm` card catalog;
- track prompts, model names, and responses;
- compare repeated runs;
- generate evaluation tables;
- later add frame extraction and OCR.
