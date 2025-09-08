# ==============================================================================
# FILE: src/utils/validators.py
# ==============================================================================

import os
import re
from pathlib import Path
from typing import Union

def validate_api_key(api_key: str) -> bool:
    """
    Validates the format of a The Movie Database (TMDB) v3 API key.

    A valid v3 key is a 32-character alphanumeric string. This function
    checks for the correct length and character set.

    Args:
        api_key: The API key string to be validated.

    Returns:
        True if the API key format is valid, False otherwise.
    """
    if not isinstance(api_key, str):
        return False
    
    # TMDB v3 API keys are 32 characters long and consist of letters and numbers.
    pattern = r'^[a-zA-Z0-9]{32}$'
    return bool(re.match(pattern, api_key))


def is_readable_file(file_path: Union[str, Path]) -> bool:
    """
    Checks if a given path points to a file that exists and is readable.

    Args:
        file_path: The path to the file (can be a string or a Path object).

    Returns:
        True if the file exists and is readable, False otherwise.
    """
    try:
        path = Path(file_path)
        # Check if it exists, is a file, and we have read access.
        return path.is_file() and os.access(path, os.R_OK)
    except (TypeError, ValueError):
        # Handles cases where file_path is not a valid path format.
        return False


def is_writable_directory(dir_path: Union[str, Path]) -> bool:
    """
    Checks if a path is a writable directory, creating it if it doesn't exist.

    This function is user-friendly: if the target directory does not exist,
    it attempts to create it, along with any necessary parent directories.

    Args:
        dir_path: The path to the directory (can be a string or a Path object).

    Returns:
        True if the path is a directory and the application has write
        permissions, False otherwise.
    """
    try:
        path = Path(dir_path)
        # Attempt to create the directory. exist_ok=True prevents errors if it's already there.
        path.mkdir(parents=True, exist_ok=True)
        # Check if it's a directory and we have write access.
        return path.is_dir() and os.access(path, os.W_OK)
    except (TypeError, OSError):
        # Handles invalid path formats or permission errors during creation.
        return False


def is_valid_language_code(language_code: str) -> bool:
    """
    Validates the ISO 639-1 language code format (e.g., 'en-US', 'fr').

    The pattern checks for a two-letter lowercase language code, optionally
    followed by a hyphen and a two-letter uppercase region code.

    Args:
        language_code: The language code string to validate.

    Returns:
        True if the format is valid, False otherwise.
    """
    if not isinstance(language_code, str):
        return False
        
    # Pattern for 'xx' or 'xx-XX' (e.g., 'en', 'en-US', 'de-DE')
    pattern = r'^[a-z]{2}(-[A-Z]{2})?$'
    return bool(re.match(pattern, language_code))