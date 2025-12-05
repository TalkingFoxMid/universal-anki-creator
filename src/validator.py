"""Response validator for Claude API responses."""

import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError


class Card(BaseModel):
    """Single flashcard model."""
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)


class SingleItemResponse(BaseModel):
    """Response for single item generation."""
    cards: List[Card] = Field(..., min_length=1)


class BatchItem(BaseModel):
    """Single item in batch response."""
    input: str
    cards: List[Card] = Field(..., min_length=1)


class BatchResponse(BaseModel):
    """Response for batch generation."""
    items: List[BatchItem] = Field(..., min_length=1)


class ResponseValidator:
    """Validates Claude API responses."""

    @staticmethod
    def _clean_control_characters(text: str) -> str:
        """
        Remove/escape invalid control characters from JSON string.

        Args:
            text: Raw text that may contain control characters

        Returns:
            Cleaned text safe for JSON parsing
        """
        # Replace control characters with escaped versions or remove them
        # Control characters are in range 0x00-0x1F and 0x7F-0x9F
        def replace_control_char(match):
            char = match.group(0)
            # Escape tab - JSON requires \t not literal tab
            if char == '\t':
                return '\\t'
            # Keep newline and carriage return (allowed in JSON strings)
            if char in ['\n', '\r']:
                return char
            # Remove other control characters
            return ''

        # Pattern matches all control characters
        control_char_pattern = re.compile(r'[\x00-\x1f\x7f-\x9f]')
        return control_char_pattern.sub(replace_control_char, text)

    @staticmethod
    def parse_json(response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from Claude.

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If JSON is invalid
        """
        # Clean up potential markdown fences
        text = response_text.strip()
        if text.startswith('```'):
            # Remove markdown code fences
            lines = text.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text = '\n'.join(lines)

        # Clean control characters
        text = ResponseValidator._clean_control_characters(text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")

    @staticmethod
    def validate_single_response(
        data: Dict[str, Any],
        expected_count: int
    ) -> List[Card]:
        """
        Validate single item response.

        Args:
            data: Parsed JSON data
            expected_count: Expected number of cards

        Returns:
            List of validated Card objects

        Raises:
            ValueError: If validation fails
        """
        try:
            response = SingleItemResponse(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid response format: {e}")

        cards = response.cards

        # Check card count
        if len(cards) != expected_count:
            raise ValueError(
                f"Expected {expected_count} cards, got {len(cards)}"
            )

        # Warn about empty content
        for i, card in enumerate(cards):
            if not card.front.strip():
                print(f"Warning: Card {i+1} has empty front")
            if not card.back.strip():
                print(f"Warning: Card {i+1} has empty back")

        return cards

    @staticmethod
    def validate_batch_response(
        data: Dict[str, Any],
        expected_count: int,
        expected_items: int
    ) -> List[BatchItem]:
        """
        Validate batch response.

        Args:
            data: Parsed JSON data
            expected_count: Expected number of cards per item
            expected_items: Expected number of items in batch

        Returns:
            List of validated BatchItem objects

        Raises:
            ValueError: If validation fails
        """
        try:
            response = BatchResponse(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid batch response format: {e}")

        items = response.items

        # Check item count
        if len(items) != expected_items:
            raise ValueError(
                f"Expected {expected_items} items, got {len(items)}"
            )

        # Check card count for each item
        for i, item in enumerate(items):
            if len(item.cards) != expected_count:
                raise ValueError(
                    f"Item {i+1}: Expected {expected_count} cards, "
                    f"got {len(item.cards)}"
                )

            # Warn about empty content
            for j, card in enumerate(item.cards):
                if not card.front.strip():
                    print(f"Warning: Item {i+1}, Card {j+1} has empty front")
                if not card.back.strip():
                    print(f"Warning: Item {i+1}, Card {j+1} has empty back")

        return items
