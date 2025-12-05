"""Output formatter for Anki import format."""

from pathlib import Path
from typing import List
from .validator import Card


class AnkiFormatter:
    """Formats cards for Anki import."""

    HEADER = "#separator:Tab\n#html:true\n#deck column:1"

    def __init__(
        self,
        output_path: str,
        deck_name: str = "Default",
        reverse: bool = False
    ):
        """
        Initialize formatter.

        Args:
            output_path: Path to output file
            deck_name: Name of Anki deck
            reverse: Swap front and back fields
        """
        self.output_path = Path(output_path)
        self.deck_name = deck_name
        self.reverse = reverse
        self.card_count = 0

    def format_card(self, card: Card) -> str:
        """
        Format single card as tab-separated line.

        Args:
            card: Card object

        Returns:
            Formatted line for Anki import
        """
        front = card.front
        back = card.back

        # Swap if reverse flag is set
        if self.reverse:
            front, back = back, front

        # Escape tabs and newlines in content
        front = front.replace('\t', ' ').replace('\n', '<br>')
        back = back.replace('\t', ' ').replace('\n', '<br>')

        return f"{self.deck_name}\t{front}\t{back}"

    def write_cards(self, cards: List[Card], append: bool = False):
        """
        Write cards to output file.

        Args:
            cards: List of Card objects
            append: Append to existing file or overwrite
        """
        mode = 'a' if append else 'w'

        with open(self.output_path, mode, encoding='utf-8') as f:
            # Write header only if creating new file
            if not append:
                f.write(self.HEADER + '\n')

            # Write cards
            for card in cards:
                line = self.format_card(card)
                f.write(line + '\n')
                self.card_count += 1

    def get_card_count(self) -> int:
        """
        Get total number of cards written.

        Returns:
            Number of cards written to file
        """
        return self.card_count

    def save_progress(self, position: int):
        """
        Save progress for recovery.

        Args:
            position: Current position in input file
        """
        progress_file = self.output_path.with_suffix('.progress')
        with open(progress_file, 'w') as f:
            f.write(str(position))

    def load_progress(self) -> int:
        """
        Load saved progress.

        Returns:
            Last saved position, or 0 if no progress file exists
        """
        progress_file = self.output_path.with_suffix('.progress')
        if progress_file.exists():
            with open(progress_file, 'r') as f:
                return int(f.read().strip())
        return 0

    def clear_progress(self):
        """Remove progress file."""
        progress_file = self.output_path.with_suffix('.progress')
        if progress_file.exists():
            progress_file.unlink()

    def create_partial_backup(self):
        """Create partial output backup."""
        if self.output_path.exists():
            partial_file = self.output_path.with_suffix('.partial')
            import shutil
            shutil.copy(self.output_path, partial_file)
