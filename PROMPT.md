Generate Anki flashcards for learning English collocations.

Card Structure:
- "front" field: Russian translation<br>English phrase with missing word as ___
- "back" field: Complete English phrase with the key word in <b style="color:red;">red bold</b>

Example JSON output:
```json
{
  "front": "принять решение<br>___ a decision",
  "back": "<b style=\"color:red;\">make</b> a decision"
}
```

Requirements:
- Use accurate Russian translations
- Replace the key verb/word with ___ on the front
- Highlight the missing word in red bold on the back
- Keep phrases natural and commonly used
