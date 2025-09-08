# ==============================================================================
# FILE: src/core/file_handler.py
# ==============================================================================

import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any

# Ensure src modules can be imported
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.logging_config import LOGGER_NAME
from src.utils.helpers import ensure_directories_exist

class FileHandler:
    """
    Handles all file input and output operations for the application.

    This class is responsible for:
    - Reading lists of media titles from various file formats (.txt, .csv, .json).
    - Writing reports, such as a list of titles that failed to download.
    """

    def __init__(self):
        self.logger = logging.getLogger(LOGGER_NAME)

    def load_titles_from_file(self, filepath: Path) -> List[str]:
        """
        Loads a list of media titles from a given file.

        This method acts as a dispatcher, determining the correct parsing
        strategy based on the file's suffix.

        Args:
            filepath: The path to the input file.

        Returns:
            A list of title strings.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file format is unsupported or malformed.
        """
        if not filepath.is_file():
            raise FileNotFoundError(f"The specified input file was not found: {filepath}")

        suffix = filepath.suffix.lower()
        self.logger.info(f"Loading titles from {filepath.name} (format: {suffix})...")

        try:
            if suffix == '.json':
                titles = self._load_from_json(filepath)
            elif suffix == '.csv':
                titles = self._load_from_csv(filepath)
            elif suffix == '.txt':
                titles = self._load_from_txt(filepath)
            else:
                raise ValueError(f"Unsupported file format: '{suffix}'. Please use .txt, .csv, or .json.")
            
            self.logger.info(f"Successfully loaded {len(titles)} titles.")
            return titles
        except Exception as e:
            self.logger.error(f"Failed to load or parse file {filepath}: {e}")
            # Re-raise the exception to be handled by the main application logic.
            raise

    def _load_from_txt(self, path: Path) -> List[str]:
        """Loads titles from a plain text file (one title per line)."""
        with path.open('r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    def _load_from_csv(self, path: Path) -> List[str]:
        """Loads titles from a CSV file, assuming titles are in the first column."""
        titles = []
        with path.open('r', encoding='utf-8', newline='') as f:
            # Use Sniffer to automatically detect if a header row exists.
            try:
                has_header = csv.Sniffer().has_header(f.read(2048))
                f.seek(0)  # Rewind the file to the beginning.
            except csv.Error:
                # Could not determine dialect, assume no header for safety
                has_header = False
                f.seek(0)

            reader = csv.reader(f)
            if has_header:
                next(reader)  # Skip the header row.

            for row in reader:
                # Ensure the row is not empty and has a value in the first column.
                if row and row[0].strip():
                    titles.append(row[0].strip())
        return titles

    def _load_from_json(self, path: Path) -> List[str]:
        """
        Loads titles from a JSON file.
        
        Supports two formats:
        1. A simple list of strings: `["Title 1", "Title 2"]`
        2. An object with a "titles" key: `{"titles": ["Title 1", "Title 2"]}`
        """
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            # Ensure all items in the list are strings.
            return [str(item).strip() for item in data if str(item).strip()]
        
        if isinstance(data, dict) and 'titles' in data and isinstance(data['titles'], list):
            return [str(item).strip() for item in data['titles'] if str(item).strip()]
            
        raise ValueError("Invalid JSON format. Must be a list of strings or an object with a 'titles' key.")

    def save_failed_titles(self, failed_titles: List[str], output_dir: Path) -> None:
        """
        Saves a list of failed titles to a text file in the output directory.

        If the list is empty, no file is created.

        Args:
            failed_titles: A list of titles that could not be downloaded.
            output_dir: The directory where the report will be saved.
        """
        if not failed_titles:
            self.logger.info("No failed downloads to report.")
            return

        ensure_directories_exist([output_dir])
        failed_file_path = output_dir / "failed_downloads.txt"
        
        try:
            with failed_file_path.open('w', encoding='utf-8') as f:
                f.write("=" * 50 + "\n")
                f.write("FAILED POSTER DOWNLOADS\n")
                f.write("=" * 50 + "\n\n")
                f.write("The following titles could not be downloaded:\n\n")
                for title in failed_titles:
                    f.write(f"- {title}\n")
            
            self.logger.info(f"Saved a report of {len(failed_titles)} failed titles to: {failed_file_path}")
        except IOError as e:
            self.logger.error(f"Could not write failed titles report to {failed_file_path}: {e}")