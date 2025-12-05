"""Input file parser for Anki generator."""

from pathlib import Path
from typing import List, Iterator


class InputParser:
    """Parses input files and manages batching."""

    def __init__(self, file_path: str, batch_size: int = 1):
        """
        Initialize parser.

        Args:
            file_path: Path to input file
            batch_size: Number of elements per batch
        """
        self.file_path = Path(file_path)
        self.batch_size = batch_size

    def read_lines(self) -> List[str]:
        """
        Read and filter input file lines.

        Returns:
            List of valid input lines

        Rules:
            - Empty lines are ignored
            - Lines starting with # are comments (ignored)
            - Strips whitespace from each line
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.file_path}")

        lines = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    lines.append(line)

        return lines

    def create_batches(self, lines: List[str]) -> Iterator[List[str]]:
        """
        Split lines into batches.

        Args:
            lines: List of input lines

        Yields:
            Batches of lines according to batch_size
        """
        for i in range(0, len(lines), self.batch_size):
            yield lines[i:i + self.batch_size]

    def parse(self) -> Iterator[List[str]]:
        """
        Parse input file and return batches.

        Yields:
            Batches of input lines
        """
        lines = self.read_lines()
        yield from self.create_batches(lines)
