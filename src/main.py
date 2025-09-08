# ==============================================================================
# FILE: src/main.py
# ==============================================================================

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# --- Path Setup ---
# Add the project's root directory (poster_downloader) to the Python path.
# This ensures that imports like `from config.config import ConfigManager` work
# correctly when running this script from any location.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# --- Application Imports ---
from config.config import ConfigManager
from src.core.downloader import UniversalPosterDownloader
from src.core.file_handler import FileHandler
from src.models.data_models import DownloadConfig, MediaType, Quality
from src.utils.helpers import parse_bulk_input
from src.utils.logging_config import setup_logging, LOGGER_NAME
from src.utils.validators import validate_api_key, is_readable_file, is_writable_directory, is_valid_language_code

def get_interactive_titles() -> List[str]:
    """Interactively prompts the user to enter titles one by one."""
    print("\n--- Interactive Mode ---")
    print("Enter titles to download. Press Enter on an empty line to start.")
    print("Type 'quit' or 'exit' to cancel.")
    
    titles = []
    while True:
        try:
            title = input(f"Enter Title #{len(titles) + 1}: ").strip()
            if not title:
                if not titles:
                    print("No titles entered. Aborting.")
                    sys.exit(0)
                break
            if title.lower() in ['quit', 'exit']:
                print("Exiting interactive mode.")
                sys.exit(0)
            titles.append(title)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)
    return titles

def create_sample_files():
    """Creates sample data and configuration files for the user."""
    print("Creating sample files...")
    # Create sample config
    ConfigManager.create_user_config_template()
    
    # Create sample data files
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    
    # TXT file
    (data_dir / "sample_titles.txt").write_text(
        "Breaking Bad\nThe Mandalorian\nInterstellar\nParasite (2019)\n",
        encoding='utf-8'
    )
    # JSON file
    (data_dir / "sample_titles.json").write_text(
        '{\n  "titles": [\n    "Game of Thrones",\n    "Chernobyl",\n    "The Dark Knight"\n  ]\n}',
        encoding='utf-8'
    )
    print(f"✅ Sample files created in '{data_dir.name}/' and '{ConfigManager.USER_CONFIG_PATH.parent.name}/' directories.")

def main():
    """The main function to run the poster downloader CLI."""
    parser = argparse.ArgumentParser(
        description="A powerful, optimized tool to download posters for movies and TV shows.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  # Download from a file using API key from config
  python src/main.py -f data/sample_titles.txt

  # Download a single title, specifying API key and quality
  python src/main.py -t "Blade Runner 2049" --api-key YOUR_KEY --quality high

  # Download a bulk list of titles as movies only
  python src/main.py -b "The Matrix, John Wick, Inception" -m movie

  # Enter interactive mode
  python src/main.py -i

  # Create sample config and data files
  python src/main.py --setup-samples
"""
    )
    
    # --- Input Group (mutually exclusive) ---
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-t", "--title", help="Download a poster for a single title.")
    input_group.add_argument("-f", "--file", type=Path, help="Path to a file with titles (.txt, .csv, .json).")
    input_group.add_argument("-b", "--bulk", help="Comma-separated list of titles.")
    input_group.add_argument("-i", "--interactive", action="store_true", help="Enter interactive mode for title input.")
    input_group.add_argument("--setup-samples", action="store_true", help="Create sample config and data files.")

    # --- Configuration Overrides ---
    config_group = parser.add_argument_group("Configuration Overrides")
    config_group.add_argument("--api-key", help="TMDB API key. Overrides config file and environment variable.")
    config_group.add_argument("-o", "--output-dir", type=Path, help="Directory to save posters.")
    config_group.add_argument("-q", "--quality", choices=[q.value for q in Quality], help="Poster quality.")
    config_group.add_argument("-m", "--media-types", nargs='+', choices=[mt.value for mt in MediaType], help="Media types to search (tv, movie).")
    config_group.add_argument("-l", "--lang", help="Language for search (e.g., en-US).")
    config_group.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Set logging verbosity.")
    config_group.add_argument("--overwrite", action="store_true", help="Overwrite existing poster files.")

    # Modern boolean flags (e.g., --zip / --no-zip)
    config_group.add_argument("--zip", action=argparse.BooleanOptionalAction, default=None, help="Zip the output folder after download.")
    config_group.add_argument("--metadata", action=argparse.BooleanOptionalAction, default=None, help="Save a metadata JSON file for each poster.")

    args = parser.parse_args()

    # --- Handle Utility Commands First ---
    if args.setup_samples:
        create_sample_files()
        sys.exit(0)
        
    # --- Layered Configuration Loading ---
    # 1. Start with default config
    config = ConfigManager.load_default_config()

    # 2. Load user config from file if it exists
    user_config_path = PROJECT_ROOT / ConfigManager.USER_CONFIG_PATH
    if user_config_path.exists():
        print(f"Loading user configuration from {user_config_path}...")
        user_config = ConfigManager.load_from_file(user_config_path)
        # Merge user config into default config
        config_dict = {**config.to_dict(), **user_config.to_dict()}
        config = DownloadConfig(**config_dict)

    # 3. Prioritize environment variable for API key
    env_api_key = os.getenv("TMDB_API_KEY")
    if env_api_key:
        config.api_key = env_api_key
        
    # 4. Override with any command-line arguments
    if args.api_key: config.api_key = args.api_key
    if args.output_dir: config.output_dir = str(args.output_dir)
    if args.quality: config.quality = Quality(args.quality)
    if args.media_types: config.media_types = [MediaType(mt) for mt in args.media_types]
    if args.lang: config.language = args.lang
    if args.overwrite: config.overwrite_existing = True
    if args.zip is not None: config.zip_output = args.zip
    if args.metadata is not None: config.save_metadata = args.metadata
    if args.log_level: config.log_level = args.log_level

    # --- Initial Setup & Validation ---
    setup_logging(config.log_level)
    logger = logging.getLogger(LOGGER_NAME)

    if not validate_api_key(config.api_key):
        logger.critical("A valid TMDB API key is required.")
        logger.critical("Provide it via --api-key, TMDB_API_KEY environment variable, or in config/user_config.json.")
        sys.exit(1)
        
    if not is_writable_directory(config.output_dir):
        logger.critical(f"Output directory is not writable: {config.output_dir}")
        sys.exit(1)
        
    if not is_valid_language_code(config.language):
        logger.critical(f"Invalid language code format: {config.language}. Must be 'xx' or 'xx-XX'.")
        sys.exit(1)

    # --- Gather Titles ---
    titles = []
    file_handler = FileHandler()
    try:
        if args.title:
            titles = [args.title]
        elif args.bulk:
            titles = parse_bulk_input(args.bulk)
        elif args.file:
            if not is_readable_file(args.file):
                logger.critical(f"Input file is not readable: {args.file}")
                sys.exit(1)
            titles = file_handler.load_titles_from_file(args.file)
        elif args.interactive:
            titles = get_interactive_titles()
    except (FileNotFoundError, ValueError) as e:
        logger.critical(f"Error processing input: {e}")
        sys.exit(1)
        
    if not titles:
        logger.error("No titles were provided to process. Exiting.")
        sys.exit(0)

    # --- Run the Downloader ---
    try:
        downloader = UniversalPosterDownloader(config)
        downloader.download_from_list(titles)
        logger.info("Download process finished.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during the download process: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()