"""Prompt builder for Claude API."""

from pathlib import Path
from typing import List, Dict, Any


class PromptBuilder:
    """Builds prompts for Claude API with caching support."""

    def __init__(
        self,
        instruction_path: str,
        prompt_path: str,
        cards_count: int = 1
    ):
        """
        Initialize prompt builder.

        Args:
            instruction_path: Path to INSTRUCTION.md template
            prompt_path: Path to user's PROMPT.md
            cards_count: Number of cards to generate per item
        """
        self.instruction_path = Path(instruction_path)
        self.prompt_path = Path(prompt_path)
        self.cards_count = cards_count

    def load_instruction(self) -> str:
        """
        Load instruction template.

        Returns:
            Instruction text with cards_count substituted

        Raises:
            FileNotFoundError: If instruction file doesn't exist
        """
        if not self.instruction_path.exists():
            raise FileNotFoundError(
                f"Instruction file not found: {self.instruction_path}"
            )

        with open(self.instruction_path, 'r', encoding='utf-8') as f:
            instruction = f.read()

        # Substitute cards_count placeholder
        return instruction.replace('{cards_count}', str(self.cards_count))

    def load_prompt(self) -> str:
        """
        Load user's prompt.

        Returns:
            User prompt text

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        if not self.prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {self.prompt_path}"
            )

        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    def build_system_prompt(self) -> str:
        """
        Build combined system prompt.

        Returns:
            Combined INSTRUCTION.md + PROMPT.md
        """
        instruction = self.load_instruction()
        user_prompt = self.load_prompt()

        return f"{instruction}\n\n---\n\n{user_prompt}"

    def build_user_prompt_single(self, input_line: str) -> str:
        """
        Build user prompt for single item.

        Args:
            input_line: Single input line

        Returns:
            User prompt text
        """
        card_word = "card" if self.cards_count == 1 else "cards"
        return (
            f"Generate {self.cards_count} {card_word} for:\n"
            f"{input_line}\n\n"
            f"Respond ONLY with JSON array. No explanations."
        )

    def build_user_prompt_batch(self, input_lines: List[str]) -> str:
        """
        Build user prompt for batch processing.

        Args:
            input_lines: List of input lines

        Returns:
            User prompt text for batch
        """
        card_word = "card" if self.cards_count == 1 else "cards"
        numbered_items = '\n'.join(
            f"{i+1}. {line}" for i, line in enumerate(input_lines)
        )

        return (
            f"Generate {self.cards_count} {card_word} for EACH of these items:\n\n"
            f"{numbered_items}\n\n"
            f"Use the BATCH format with 'items' array. Include the original input text for each item."
        )

    def create_system_message(self) -> Dict[str, Any]:
        """
        Create system message with caching.

        Returns:
            System message dict with cache_control
        """
        system_text = self.build_system_prompt()

        return {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        }

    def create_user_message_single(self, input_line: str) -> Dict[str, Any]:
        """
        Create user message for single item.

        Args:
            input_line: Single input line

        Returns:
            User message dict
        """
        return {
            "role": "user",
            "content": self.build_user_prompt_single(input_line)
        }

    def create_user_message_batch(
        self,
        input_lines: List[str]
    ) -> Dict[str, Any]:
        """
        Create user message for batch processing.

        Args:
            input_lines: List of input lines

        Returns:
            User message dict
        """
        return {
            "role": "user",
            "content": self.build_user_prompt_batch(input_lines)
        }
