# ==============================================================================
# FILE: src/utils/helpers.py
# ==============================================================================

import re
import unicodedata
from pathlib import Path
from typing import Iterable

def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Cleans and sanitizes a string to be a valid and safe filename.

    The process is as follows:
    1.  Handles None or empty string inputs by returning a default.
    2.  Normalizes Unicode characters to their closest ASCII equivalent.
    3.  Replaces illegal filename characters (`<>:"/\\|?*`) with underscores.
    4.  Collapses consecutive whitespace characters into a single underscore.
    5.  Removes any characters that are not alphanumeric, underscores, or hyphens.
    6.  Strips leading/trailing underscores or hyphens.
    7.  Truncates the name to a safe maximum length.

    Args:
        filename: The original string to be sanitized.
        max_length: The maximum allowed length of the final filename.

    Returns:
        A filesystem-safe string.
    """
    # 1. Handle invalid input
    if not isinstance(filename, str) or not filename.strip():
        return "untitled"

    # 2. Normalize Unicode to ASCII
    # 'NFKD' decomposes characters, and encode/decode removes the diacritics
    sanitized = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')

    # 3. Replace illegal characters (common across OSes)
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)

    # 4. Collapse whitespace to single underscore
    sanitized = re.sub(r'\s+', '_', sanitized)
    
    # 5. Remove any remaining invalid characters (whitelist approach)
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', sanitized)
    
    # 6. Collapse multiple underscores that may have been created
    sanitized = re.sub(r'__+', '_', sanitized)

    # 7. Strip leading/trailing underscores or hyphens
    sanitized = sanitized.strip('_-')

    # 8. Truncate to the desired max length
    sanitized = sanitized[:max_length]
    
    # Final check: if the process resulted in an empty string
    return sanitized or "untitled"


def ensure_directories_exist(paths: Iterable[Path]) -> None:
    """
    Ensures that all directories in the provided iterable exist.

    This function iterates through a list or tuple of Path objects and
    creates each directory, including any necessary parent directories.
    It gracefully handles cases where the directory already exists.

    Args:
        paths: An iterable of pathlib.Path objects for the directories to create.
    """
    for path in paths:
        if path:
            path.mkdir(parents=True, exist_ok=True)


def parse_bulk_input(bulk_string: str) -> list[str]:
    """
    Parses a comma-separated string into a clean list of individual items.
    
    Example:
        `"Breaking Bad, The Office  , , Arcane"` -> `['Breaking Bad', 'The Office', 'Arcane']`

    Args:
        bulk_string: The raw, comma-delimited input string.

    Returns:
        A list of strings, with whitespace removed and empty entries discarded.
    """
    if not isinstance(bulk_string, str):
        return []
    return [item.strip() for item in bulk_string.split(',') if item and item.strip()]


def format_file_size(size_bytes: int) -> str:
    """
    Converts a size in bytes to a human-readable string format (B, KB, MB, GB).

    Uses a base of 1024 for calculations (kibibytes, mebibytes, etc.).

    Args:
        size_bytes: The size of the file in bytes.

    Returns:
        A formatted string, e.g., "5.2MB".
    """
    if not isinstance(size_bytes, int) or size_bytes < 0:
        return "0B"
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    # Use a while loop to find the correct unit
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float /= 1024.0
        i += 1
        
    return f"{size_float:.1f}{size_names[i]}"