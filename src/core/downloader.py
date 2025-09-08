# ==============================================================================
# FILE: src/core/downloader.py
# ==============================================================================

import json
import logging
import time
import requests
import zipfile
from pathlib import Path
from typing import List, Optional

# Ensure src modules can be imported
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.data_models import DownloadConfig, DownloadResult, DownloadStats, MediaInfo
from src.core.api_client import TMDBApiClient
from src.core.file_handler import FileHandler
from src.utils.helpers import sanitize_filename, ensure_directories_exist, format_file_size
from src.utils.logging_config import LOGGER_NAME

class UniversalPosterDownloader:
    """
    The main class for orchestrating the poster download process.
    
    This class ties together the API client, file handler, and configuration
    to manage searching, downloading, and saving posters and their metadata.
    """

    def __init__(self, config: DownloadConfig):
        self.config = config
        self.logger = logging.getLogger(LOGGER_NAME)
        self.api_client = TMDBApiClient(config)
        self.file_handler = FileHandler()
        self.stats = DownloadStats()

        # Prepare output directories
        self.output_path = Path(self.config.output_dir)
        self.metadata_path = self.output_path.parent / "metadata"
        ensure_directories_exist([self.output_path, self.metadata_path])

    def _find_best_match(self, title: str) -> Optional[MediaInfo]:
        """
        Intelligently searches for the best media match for a given title.

        It searches across all configured media types and languages, then uses
        backup languages if no initial results are found. The best match is
        determined by TMDB's popularity metric.

        Args:
            title: The title of the media to search for.

        Returns:
            A MediaInfo object for the best match, or None if no suitable match is found.
        """
        self.logger.debug(f"Finding best match for '{title}'...")
        
        # Search primary language first across all specified media types
        for media_type in self.config.media_types:
            results = self.api_client.search_media(title, media_type, self.config.language)
            if results:
                best_result = results[0] # Results are pre-sorted by popularity
                self.logger.info(f"Found primary match for '{title}': '{best_result.title}' ({best_result.media_type.value})")
                return best_result

        # If no results, try backup languages
        self.logger.warning(f"No results for '{title}' in primary language. Trying backup languages...")
        for lang in self.config.backup_languages:
            for media_type in self.config.media_types:
                results = self.api_client.search_media(title, media_type, lang)
                if results:
                    best_result = results[0]
                    self.logger.info(f"Found backup match for '{title}' in language '{lang}': '{best_result.title}'")
                    return best_result

        self.logger.error(f"No match found for '{title}' in any configured language.")
        return None

    def _save_metadata(self, safe_filename: str, media_info: MediaInfo, poster_url: str):
        """Saves a JSON file with detailed metadata for a downloaded poster."""
        metadata = {
            "query": media_info.title,
            "download_details": {
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "poster_url": poster_url,
                "quality_setting": self.config.quality.value,
            },
            "tmdb_data": media_info.__dict__  # Convert MediaInfo dataclass to dict
        }
        # Convert enums to strings for JSON
        metadata['tmdb_data']['media_type'] = media_info.media_type.value

        metadata_filepath = self.metadata_path / f"{safe_filename}_meta.json"
        try:
            with metadata_filepath.open('w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)
            self.logger.debug(f"Metadata saved for '{safe_filename}'")
        except IOError as e:
            self.logger.error(f"Failed to save metadata for '{safe_filename}': {e}")

    def download_single_poster(self, title: str) -> DownloadResult:
        """
        Handles the complete download process for a single title.

        This includes checking for existing files, finding the best match,
        downloading the image with retries, and saving metadata.

        Args:
            title: The title of the media to download a poster for.

        Returns:
            A DownloadResult object detailing the outcome.
        """
        safe_filename = sanitize_filename(title)
        poster_filepath = self.output_path / f"{safe_filename}.jpg"

        if not self.config.overwrite_existing and poster_filepath.exists():
            self.logger.info(f"Skipping '{title}', poster already exists.")
            self.stats.skipped += 1
            return DownloadResult(title=title, success=True, file_path=str(poster_filepath))

        media_info = self._find_best_match(title)
        if not media_info or not media_info.poster_path:
            self.stats.failed += 1
            self.stats.failed_titles.append(title)
            return DownloadResult(title=title, success=False, error_message="No suitable match or poster found on TMDB.")
        
        poster_url = self.api_client.get_poster_url(media_info.poster_path)
        if not poster_url:
            self.stats.failed += 1
            self.stats.failed_titles.append(title)
            return DownloadResult(title=title, success=False, error_message="Could not construct a valid poster URL.")
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = requests.get(poster_url, stream=True, timeout=30)
                response.raise_for_status()

                with poster_filepath.open('wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size_str = format_file_size(poster_filepath.stat().st_size)
                self.logger.info(f"Successfully downloaded '{title}' ({file_size_str}).")

                if self.config.save_metadata:
                    self._save_metadata(safe_filename, media_info, poster_url)

                self.stats.successful += 1
                return DownloadResult(title=title, success=True, file_path=str(poster_filepath), media_info=media_info, attempts=attempt)

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt}/{self.config.max_retries} for '{title}' failed: {e}")
                if attempt < self.config.max_retries:
                    time.sleep(1) # Wait a second before retrying
                else:
                    self.stats.failed += 1
                    self.stats.failed_titles.append(title)
                    return DownloadResult(title=title, success=False, error_message=str(e), attempts=attempt)
        
        # This line should not be reachable, but is included for completeness
        return DownloadResult(title=title, success=False, error_message="Download failed after all retries.")

    def download_from_list(self, titles: List[str]) -> DownloadStats:
        """
        Manages the batch download process for a list of titles.

        Args:
            titles: A list of media titles to process.

        Returns:
            A DownloadStats object summarizing the entire session.
        """
        self.stats = DownloadStats(total=len(titles))
        self.logger.info(f"Starting batch download for {self.stats.total} titles.")
        self.logger.info(f"Output Directory: {self.output_path.resolve()}")
        self.logger.info(f"Quality: {self.config.quality.value}")

        for i, title in enumerate(titles, 1):
            self.logger.info(f"--- Processing [{i}/{self.stats.total}]: {title} ---")
            self.download_single_poster(title)
        
        self._print_summary()
        self.file_handler.save_failed_titles(self.stats.failed_titles, self.output_path)
        
        if self.config.zip_output:
            self._create_zip_archive()
            
        return self.stats

    def _print_summary(self):
        """Prints a formatted summary of the download session to the console."""
        print("\n" + "="*60)
        print("📊 DOWNLOAD SESSION SUMMARY")
        print("="*60)
        print(f"Total Items Processed: {self.stats.total}")
        print(f"✅ Successful: {self.stats.successful}")
        print(f"⏭️ Skipped (Already Existed): {self.stats.skipped}")
        print(f"❌ Failed: {self.stats.failed}")
        print("="*60)
        
        if self.stats.failed > 0:
            print(f"A list of {self.stats.failed} failed titles has been saved to:")
            print(f"  -> {self.output_path.resolve() / 'failed_downloads.txt'}")

    def _create_zip_archive(self):
        """Creates a zip archive of the downloaded posters."""
        zip_path = self.output_path.parent / f"{self.output_path.name}.zip"
        poster_files = list(self.output_path.glob("*.jpg"))

        if not poster_files:
            self.logger.warning("No posters were downloaded, skipping zip archive creation.")
            return

        self.logger.info(f"Creating zip archive at {zip_path}...")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in poster_files:
                    zipf.write(file, file.name)
            
            zip_size = format_file_size(zip_path.stat().st_size)
            self.logger.info(f"📦 Successfully created zip archive with {len(poster_files)} posters ({zip_size}).")
        except (zipfile.BadZipFile, OSError) as e:
            self.logger.error(f"Failed to create zip archive: {e}")