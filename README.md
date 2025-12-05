# Universal Anki Deck Generator

A flexible CLI tool that generates Anki flashcards using Claude API. Completely format-agnostic - you define what to generate in `PROMPT.md`.

## Features

- Format-agnostic: Works with any language, content type, or card structure
- Prompt caching: Saves ~90% on API costs for repeated requests
- Batch processing: Process multiple items in a single API call
- Error recovery: Automatic retries with progress saving
- Flexible output: Supports custom deck names and front/back reversal

## Installation

### Prerequisites

- Python 3.9 or higher
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### Setup

1. Clone or download this repository:
```bash
cd universal-anki-generator
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up your API key:
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Quick Start

### 1. Create a PROMPT.md file

This file defines how cards should be generated. Example for English vocabulary:

```markdown
Generate flashcards for learning English words.

For each word, create cards with DIFFERENT example sentences.

Front: English sentence with the target word highlighted: <b style="color:red;">word</b>
Back: Russian translation with the target word highlighted the same way. Add <br><br> and a brief definition in English.

Sentences should be natural and from different contexts.
```

### 2. Create an INPUT.txt file

Add one item per line:

```
busy
to hand over
```

### 3. Run the generator

```bash
anki-gen -p PROMPT.md -c 3 -d "English::Vocabulary" INPUT.txt
```

This will:
- Read items from `INPUT.txt`
- Generate 3 cards per item
- Save to `OUTPUT.txt` (ready for Anki import)
- Create deck named "English::Vocabulary"

### 4. Import into Anki

1. Open Anki
2. File → Import
3. Select `OUTPUT.txt`
4. Anki will automatically detect the format and import your cards

## Usage

```bash
anki-gen [OPTIONS] <INPUT_FILE>
```

### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--prompt` | `-p` | Path to PROMPT.md | `./PROMPT.md` |
| `--output` | `-o` | Path to OUTPUT.txt | `./OUTPUT.txt` |
| `--deck` | `-d` | Deck name | `Default` |
| `--reverse` | `-r` | Swap front/back | `false` |
| `--cards` | `-c` | Cards per input item | `1` |
| `--batch-size` | `-b` | Items per API request | `1` |
| `--model` | `-m` | Claude model | `claude-sonnet-4-20250514` |
| `--dry-run` | | Show requests without executing | `false` |
| `--verbose` | `-v` | Verbose output | `false` |

### Examples

#### Basic usage
```bash
anki-gen -p vocabulary_prompt.md input.txt
```

#### With reverse (front ↔ back) and custom deck
```bash
anki-gen -p math_prompt.md -r -d "Math::Integrals" formulas.txt
```

#### Batch mode with 3 cards per item
```bash
anki-gen -p history_prompt.md -b 5 -c 3 -o history.txt dates.txt
```

#### Preview without generating (dry run)
```bash
anki-gen -p prompt.md --dry-run input.txt
```

## Input Format

### INPUT.txt

One item per line. Each line becomes N cards (specified by `-c`).

```
busy
to hand over
∫x²dx
Столица Франции
What is polymorphism?
```

Rules:
- Empty lines are ignored
- Lines starting with `#` are comments (ignored)
- No specific format required - Claude interprets based on your PROMPT.md

## Prompt Examples

### English Vocabulary

```markdown
Generate flashcards for English vocabulary learning.

Create 3 different example sentences for each word.

Front: English sentence with <b style="color:red;">target word</b>
Back: Russian translation with <b style="color:red;">перевод</b><br><br>brief English definition

Make sentences natural and varied in context.
```

### Math Formulas

```markdown
Generate calculus flashcards.

Front: The integral expression (use HTML: &int; for ∫)
Back: Solution + brief explanation of the method used
```

### History Dates

```markdown
Generate flashcards for memorizing historical dates.

Front: Date and brief description
Back: Event name

Example:
Front: "June 18, 1815 — decisive battle ending the Napoleonic Wars"
Back: "Battle of Waterloo"
```

### Programming Concepts

```markdown
Flashcards for programming concepts.

Front: Question about the concept
Back: Concise answer + code example in ```python``` block
```

## Project Structure

```
anki-generator/
├── src/
│   ├── __init__.py
│   ├── main.py          # CLI entry point
│   ├── parser.py        # Input file parsing
│   ├── prompt.py        # Prompt building
│   ├── api.py           # Claude API client
│   ├── formatter.py     # Output formatting
│   └── validator.py     # Response validation
├── templates/
│   └── INSTRUCTION.md   # Built-in instruction template
├── tests/
├── pyproject.toml
├── README.md
├── SPEC.md
└── .env.example
```

## How It Works

1. **Input Parsing**: Reads INPUT.txt, filters comments and empty lines
2. **Prompt Building**: Combines INSTRUCTION.md + PROMPT.md with cache_control
3. **API Call**: Sends batched requests to Claude API
4. **Validation**: Validates JSON response and card count
5. **Formatting**: Converts to Anki import format (tab-separated)
6. **Output**: Writes to OUTPUT.txt with proper headers

## Cost Optimization

### Prompt Caching

The system prompt (INSTRUCTION.md + PROMPT.md) is cached using Claude's prompt caching feature:
- First request: ~500 tokens
- Subsequent requests: ~50 tokens (90% savings)

### Batch Processing

Process multiple items in one API call to reduce overhead:

| Batch Size | Requests (100 items) | Efficiency |
|------------|---------------------|------------|
| 1          | 100                 | Low        |
| 5          | 20                  | Medium     |
| 10         | 10                  | High       |

Recommended: `--batch-size 5` for balance of reliability and cost.

### Estimated Cost

For 100 items with batch-size=5 and cards=3:
- Input tokens: ~2,000
- Output tokens: ~30,000
- Cost: ~$0.10-0.15 (Claude Sonnet)

## Error Handling

### Automatic Retries

- Rate limits (429): Exponential backoff
- Server errors (5xx): Retry up to 3 times
- Invalid JSON: Parse and retry once
- Timeout: Retry with smaller batch

### Recovery

If processing fails mid-way:
- Progress saved in `OUTPUT.txt.progress`
- Partial output saved in `OUTPUT.txt.partial`
- Resume by rerunning the same command

## Development

### Install in development mode

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

## Troubleshooting

### "API key not provided"
Set your API key in `.env` file or export as environment variable:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### "Prompt file not found"
Ensure PROMPT.md exists in the current directory or provide full path:
```bash
anki-gen -p /path/to/PROMPT.md input.txt
```

### Rate limit errors
Reduce batch size or add delay between requests:
```bash
anki-gen -b 1 input.txt
```

## License

MIT License - See SPEC.md for detailed specification.

## Contributing

This tool is designed to be flexible and extensible. Contributions welcome!

Areas for improvement:
- Async API calls for parallel processing
- Web UI for card preview
- AnkiConnect integration for direct import
- Local caching with SQLite
- Streaming output
