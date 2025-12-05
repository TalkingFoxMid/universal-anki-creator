# Anki Deck Generator — Спецификация

## Обзор

Универсальный CLI-генератор Anki-колод через Claude API. Полностью format-agnostic: что генерировать — определяет пользователь в PROMPT.md.

**Не привязан к:**
- Конкретному языку
- Типу контента (слова, фразы, вопросы, формулы...)
- Структуре front/back

---

## Входные файлы

### INPUT.txt

Произвольные строки данных. Каждая строка — один "элемент" для генерации карточек.

```
busy
to hand over - передать
∫x²dx
Столица Франции
What is polymorphism?
```

**Правила:**
- Одна строка = один элемент = N карточек (задаётся параметром `-c`)
- Формат строки не фиксирован — Claude интерпретирует согласно PROMPT.md
- Пустые строки игнорируются
- Строки, начинающиеся с `#` — комментарии (игнорируются)

### INSTRUCTION.md

Технические правила для Claude. Содержит:
- Формат JSON-ответа
- Требование возвращать ровно N карточек
- Базовые ограничения

**Этот файл поставляется с приложением** (минимальный, ~200 токенов).

### PROMPT.md (обязательный)

**Главный файл** — определяет всю логику генерации:
- Что такое "front" и "back"
- Язык(и) контента
- Стиль, формат, HTML-разметка
- Любые специфичные правила

**Пример для английской лексики:**
```markdown
Ты генерируешь карточки для изучения английских слов.

Для каждого элемента создай 3 карточки с РАЗНЫМИ предложениями.

Front: Английское предложение. Целевое слово выдели: <b style="color:red;">слово</b>
Back: Русский перевод. Целевое слово выдели так же. Добавь <br><br> и краткое определение на английском.

Предложения должны быть естественными, разного контекста.
```

**Пример для математики:**
```markdown
Генерируй карточки для запоминания интегралов.

Front: Интеграл в LaTeX формате
Back: Решение с пошаговым объяснением
```

**Пример для истории:**
```markdown
Генерируй карточки по историческим датам.

Front: Событие (без даты)
Back: Дата + краткое описание последствий
```

---

## Параметры командной строки

```bash
anki-gen [OPTIONS] <INPUT_FILE>
```

| Параметр | Короткий | Описание | Default |
|----------|----------|----------|---------|
| `--prompt` | `-p` | Путь к PROMPT.md | `./PROMPT.md` |
| `--output` | `-o` | Путь к OUTPUT.txt | `./OUTPUT.txt` |
| `--deck` | `-d` | Название колоды | `Default` |
| `--reverse` | `-r` | Поменять front/back местами | `false` |
| `--cards` | `-c` | Количество карточек на элемент | `1` |
| `--batch-size` | `-b` | Элементов в одном API-запросе | `1` |
| `--model` | `-m` | Модель Claude | `claude-sonnet-4-20250514` |
| `--dry-run` | | Показать запросы без выполнения | `false` |
| `--verbose` | `-v` | Подробный вывод | `false` |

**Примеры:**

```bash
# Базовое использование
anki-gen -p vocabulary_prompt.md input.txt

# С reverse (front↔back) и кастомной декой
anki-gen -p math_prompt.md -r -d "Math::Integrals" formulas.txt

# Batch-режим, 3 карточки на элемент
anki-gen -p history_prompt.md -b 5 -c 3 -o history.txt dates.txt
```

---

## Выходной файл

### Формат OUTPUT.txt

```
#separator:Tab
#html:true
#deck column:1

[Deck_Name]	[Front]	[Back]
[Deck_Name]	[Front]	[Back]
...
```

### Флаг --reverse

Без `-r`:
```
Deck	{front}	{back}
```

С `-r`:
```
Deck	{back}	{front}
```

Просто меняет местами — для случаев, когда нужно "вспомнить" исходный элемент.

---

## Архитектура

### Компоненты

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                         │
│                    (argument parsing)                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      Core Engine                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ InputParser │  │ PromptBuilder│  │ OutputFormatter    │  │
│  │             │  │             │  │                     │  │
│  │ - read file │  │ - system    │  │ - validate cards    │  │
│  │ - filter    │  │ - user      │  │ - format output     │  │
│  │ - batch     │  │ - caching   │  │ - write file        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     Claude API Client                        │
│                                                              │
│  - Prompt caching (cache_control)                           │
│  - Rate limiting                                             │
│  - Retry logic                                               │
│  - JSON response parsing                                     │
└─────────────────────────────────────────────────────────────┘
```

### Поток данных

```
INPUT.txt ──► Parser ──► Batcher ──► API Client ──► Validator ──► OUTPUT.txt
                              │
              INSTRUCTION.md ─┤
              PROMPT.md ──────┘
```

---

## API Integration

### System Prompt (кэшируется)

Собирается из:
1. INSTRUCTION.md (технический, ~200 токенов)
2. PROMPT.md (пользовательский)

```json
{
  "role": "system",
  "content": [
    {
      "type": "text",
      "text": "<INSTRUCTION.md>\n\n---\n\n<PROMPT.md>",
      "cache_control": { "type": "ephemeral" }
    }
  ]
}
```

### User Prompt

```
Generate {cards_count} card(s) for:
{input_line}

Respond ONLY with JSON array. No explanations.
```

### Ожидаемый ответ (JSON)

```json
{
  "cards": [
    { "front": "...", "back": "..." },
    { "front": "...", "back": "..." },
    { "front": "...", "back": "..." }
  ]
}
```

**Всё.** Что внутри `front` и `back` — определяет PROMPT.md.

### Batch-режим

При `--batch-size 3`:

```
Generate {cards_count} card(s) for EACH item:
1. busy
2. ∫x²dx  
3. Битва при Ватерлоо

Respond with JSON. Group cards by item.
```

Ответ:
```json
{
  "items": [
    {
      "input": "busy",
      "cards": [
        { "front": "...", "back": "..." }
      ]
    },
    ...
  ]
}
```

---

## INSTRUCTION.md (встроенный, минимальный)

```markdown
# Card Generation Rules

You generate Anki flashcards. Follow the user's PROMPT exactly.

## Output Format
Return ONLY valid JSON. No markdown fences, no explanations.

## Schema
{
  "cards": [
    { "front": "...", "back": "..." }
  ]
}

## Rules
- Generate exactly {cards_count} cards per input
- Each card MUST have both "front" and "back" fields
- Content of front/back is defined by user's PROMPT
- If generating multiple cards for one input, make them meaningfully different
```

**~150 токенов** — остальное определяет пользователь в PROMPT.md.

---

## Оптимизация токенов

### 1. Prompt Caching

Claude API кэширует system prompt при использовании `cache_control: { type: "ephemeral" }`.

**Экономия:** ~90% стоимости system prompt при повторных запросах в рамках сессии.

### 2. Минимальный INSTRUCTION.md

Встроенная инструкция — ~150 токенов. Вся логика в PROMPT.md пользователя.

### 3. Batch Processing

| Batch Size | Запросов на 100 элементов | Overhead |
|------------|---------------------------|----------|
| 1          | 100                       | Высокий  |
| 5          | 20                        | Средний  |
| 10         | 10                        | Низкий   |

**Рекомендация:** `--batch-size 5` — баланс надёжности и экономии.

### 4. Оценка потребления

**На 100 элементов, batch-size=5, cards=3:**

| Компонент | Токены |
|-----------|--------|
| System prompt (INSTRUCTION + PROMPT, первый запрос) | ~500 |
| System prompt (кэш, 19 запросов) | ~50 × 19 ≈ 950 |
| User prompts (20 запросов) | ~30 × 20 = 600 |
| Responses (300 карточек) | ~100 × 300 = 30,000 |
| **Итого input** | ~2,000 |
| **Итого output** | ~30,000 |

**Стоимость (Claude Sonnet):** ~$0.10-0.15 за 100 элементов.

---

## Обработка ошибок

### API Errors

| Ошибка | Действие |
|--------|----------|
| Rate limit (429) | Exponential backoff, retry |
| Server error (5xx) | Retry 3 times |
| Invalid JSON response | Log, retry once |
| Timeout | Retry with smaller batch |

### Validation Errors

- Неверное количество карточек — retry
- Отсутствует поле `front` или `back` — retry
- Пустое значение — warning, продолжить

### Recovery

При ошибке в середине обработки:
- Сохранить прогресс в `OUTPUT.txt.partial`
- Записать позицию в `OUTPUT.txt.progress`
- При перезапуске продолжить с последней позиции

---

## Структура проекта

```
anki-generator/
├── src/
│   ├── main.py           # Entry point, CLI
│   ├── parser.py         # Input file parsing
│   ├── prompt.py         # Prompt building
│   ├── api.py            # Claude API client
│   ├── formatter.py      # Output formatting
│   └── validator.py      # Response validation
├── templates/
│   └── INSTRUCTION.md    # Default instruction
├── tests/
│   ├── test_parser.py
│   ├── test_api.py
│   └── fixtures/
├── pyproject.toml
├── README.md
└── .env.example          # ANTHROPIC_API_KEY
```

---

## Зависимости

```toml
[project]
dependencies = [
    "anthropic>=0.40.0",
    "click>=8.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

---

## Примеры использования

### English Vocabulary

```bash
# PROMPT.md
cat > prompt.md << 'EOF'
Генерируй карточки для английских слов.

Front: Английское предложение с <b style="color:red;">словом</b>
Back: Русский перевод с <b style="color:red;">переводом</b><br><br>краткое определение (EN)

Создай 3 разных предложения для каждого слова.
EOF

# INPUT.txt
echo "busy" > input.txt
echo "to hand over" >> input.txt

# Run
anki-gen -p prompt.md -c 3 -d "English::Vocabulary" input.txt
```

### Math Formulas

```bash
# PROMPT.md  
cat > math_prompt.md << 'EOF'
Generate calculus flashcards.

Front: The integral expression (use HTML: &int; for ∫)
Back: Solution + brief explanation of the method used
EOF

# INPUT.txt
echo "∫x²dx" > integrals.txt
echo "∫e^x dx" >> integrals.txt

# Run
anki-gen -p math_prompt.md -d "Math::Calculus" integrals.txt
```

### History Dates (Reverse)

```bash
# PROMPT.md
cat > history_prompt.md << 'EOF'
Карточки для запоминания исторических дат.

Front: Дата и краткое описание
Back: Название события

Пример:
Front: "18 июня 1815 — решающее сражение, положившее конец Наполеоновским войнам"
Back: "Битва при Ватерлоо"
EOF

# С флагом -r пользователь будет видеть описание и вспоминать событие
anki-gen -p history_prompt.md -r -d "History::Dates" events.txt
```

### Programming Concepts

```bash
# PROMPT.md
cat > code_prompt.md << 'EOF'
Flashcards for programming concepts.

Front: Question about the concept
Back: Concise answer + code example in ```python``` block
EOF

anki-gen -p code_prompt.md -d "Programming::Python" concepts.txt
```

---

## TODO / Future Improvements

- [ ] Async API calls для параллельной обработки
- [ ] Web UI для preview карточек
- [ ] Интеграция с AnkiConnect для прямого импорта
- [ ] Кэширование результатов локально (SQLite)
- [ ] Streaming output (писать карточки по мере генерации)
