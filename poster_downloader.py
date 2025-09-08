#!/usr/bin/env python3
"""
Universal Media Poster Downloader

A flexible script to download movie/TV show posters from TMDB with multiple input methods,
configuration options, and advanced features.

Usage:
    python poster_downloader.py --help
    python poster_downloader.py --file shows.txt
    python poster_downloader.py --interactive
    python poster_downloader.py --bulk "Breaking Bad,The Office,Friends"
"""

import os
import sys
import json
import csv
import argparse
import requests
import zipfile
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote
from dataclasses import dataclass, asdict
import logging

@dataclass
class Config:
    """Configuration class for the downloader."""
    api_key: str = ""
    output_dir: str = "posters"
    language: str = "en-US"
    delay: float = 0.5
    quality: str = "original"  # original, w500, w342, w185
    media_types: List[str] = None
    max_retries: int = 3
    zip_output: bool = True
    save_metadata: bool = True
    overwrite_existing: bool = False
    backup_languages: List[str] = None
    
    def __post_init__(self):
        if self.media_types is None:
            self.media_types = ["tv", "movie"]
        if self.backup_languages is None:
            self.backup_languages = ["en", "ja", "es"]

class UniversalPosterDownloader:
    """Universal poster downloader with multiple input methods and advanced features."""
    
    BASE_URL = "https://api.themoviedb.org/3"
    IMG_BASE = "https://image.tmdb.org/t/p"
    
    # Quality options
    QUALITY_OPTIONS = {
        "original": "original",
        "high": "w500",
        "medium": "w342", 
        "low": "w185"
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "failed_titles": []
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('poster_downloader.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
    
    def load_titles_from_file(self, filepath: str) -> List[str]:
        """Load titles from various file formats (txt, csv, json)."""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        titles = []
        
        try:
            if filepath.suffix.lower() == '.json':
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        titles = data
                    elif isinstance(data, dict) and 'titles' in data:
                        titles = data['titles']
                    else:
                        titles = list(data.values())
            
            elif filepath.suffix.lower() == '.csv':
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    titles = [row[0].strip() for row in reader if row and row[0].strip()]
            
            else:  # Default to txt
                with open(filepath, 'r', encoding='utf-8') as f:
                    titles = [line.strip() for line in f if line.strip()]
        
        except Exception as e:
            self.logger.error(f"Error reading file {filepath}: {e}")
            raise
        
        self.logger.info(f"Loaded {len(titles)} titles from {filepath}")
        return titles
    
    def interactive_input(self) -> List[str]:
        """Interactive mode for inputting titles."""
        print("\n🎬 Interactive Mode")
        print("Enter show/movie titles one by one. Press Enter on empty line to finish.")
        print("Commands: 'quit' to exit, 'list' to show current titles")
        
        titles = []
        while True:
            try:
                title = input(f"Title #{len(titles) + 1}: ").strip()
                
                if not title:
                    break
                elif title.lower() == 'quit':
                    sys.exit(0)
                elif title.lower() == 'list':
                    print(f"Current titles: {titles}")
                    continue
                else:
                    titles.append(title)
                    print(f"✅ Added: {title}")
                    
            except KeyboardInterrupt:
                print("\n\nOperation cancelled.")
                sys.exit(0)
        
        return titles
    
    def search_media(self, title: str, media_type: str) -> Optional[Dict]:
        """Search for a specific media type."""
        search_url = f"{self.BASE_URL}/search/{media_type}"
        params = {
            "api_key": self.config.api_key,
            "query": title,
            "language": self.config.language
        }
        
        try:
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            results = response.json().get("results", [])
            
            if results:
                return {
                    "data": results[0],
                    "media_type": media_type
                }
        except requests.RequestException as e:
            self.logger.debug(f"Search failed for {title} ({media_type}): {e}")
        
        return None
    
    def get_poster_info(self, title: str) -> Optional[Tuple[str, Dict]]:
        """Get poster URL and metadata for a title."""
        # Try each configured media type
        for media_type in self.config.media_types:
            result = self.search_media(title, media_type)
            if result:
                poster_path = result["data"].get("poster_path")
                if poster_path:
                    quality = self.QUALITY_OPTIONS.get(self.config.quality, "original")
                    poster_url = f"{self.IMG_BASE}/{quality}{poster_path}"
                    return poster_url, result
        
        # Try backup languages if main language fails
        original_language = self.config.language
        for backup_lang in self.config.backup_languages:
            if backup_lang == original_language.split('-')[0]:
                continue
            
            self.config.language = backup_lang
            for media_type in self.config.media_types:
                result = self.search_media(title, media_type)
                if result:
                    poster_path = result["data"].get("poster_path")
                    if poster_path:
                        quality = self.QUALITY_OPTIONS.get(self.config.quality, "original")
                        poster_url = f"{self.IMG_BASE}/{quality}{poster_path}"
                        self.config.language = original_language  # Reset
                        return poster_url, result
        
        self.config.language = original_language  # Reset
        return None, None
    
    def sanitize_filename(self, filename: str) -> str:
        """Create a safe filename."""
        # Remove/replace problematic characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_()[]"
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)
        # Clean up multiple spaces/underscores
        sanitized = "_".join(sanitized.split())
        return sanitized.replace(" ", "_")[:100]  # Limit length
    
    def download_poster(self, title: str) -> bool:
        """Download poster for a single title."""
        safe_filename = self.sanitize_filename(title)
        poster_path = Path(self.config.output_dir) / f"{safe_filename}.jpg"
        metadata_path = Path(self.config.output_dir) / f"{safe_filename}_metadata.json"
        
        # Skip if exists and not overwriting
        if poster_path.exists() and not self.config.overwrite_existing:
            self.logger.info(f"⏭️ Skipping {title} (already exists)")
            self.stats["skipped"] += 1
            return True
        
        # Get poster info
        poster_url, metadata = self.get_poster_info(title)
        
        if not poster_url:
            self.logger.warning(f"❌ No poster found for: {title}")
            self.stats["failed"] += 1
            self.stats["failed_titles"].append(title)
            return False
        
        # Download with retries
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(poster_url)
                response.raise_for_status()
                
                # Save poster
                with open(poster_path, "wb") as f:
                    f.write(response.content)
                
                # Save metadata if requested
                if self.config.save_metadata and metadata:
                    metadata_info = {
                        "title": title,
                        "download_info": {
                            "poster_url": poster_url,
                            "quality": self.config.quality,
                            "language": self.config.language,
                            "download_date": time.strftime("%Y-%m-%d %H:%M:%S")
                        },
                        "tmdb_data": metadata
                    }
                    with open(metadata_path, "w", encoding="utf-8") as f:
                        json.dump(metadata_info, f, indent=2, ensure_ascii=False)
                
                media_type = metadata.get("media_type", "unknown") if metadata else "unknown"
                self.logger.info(f"✅ Downloaded: {title} ({media_type})")
                self.stats["successful"] += 1
                return True
                
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    self.logger.warning(f"⚠️ Attempt {attempt + 1} failed for {title}: {e}")
                    time.sleep(self.config.delay * 2)  # Longer delay on retry
                else:
                    self.logger.error(f"❌ Failed to download {title} after {self.config.max_retries} attempts: {e}")
                    self.stats["failed"] += 1
                    self.stats["failed_titles"].append(title)
                    return False
        
        return False
    
    def download_all(self, titles: List[str]):
        """Download posters for all titles."""
        self.stats["total"] = len(titles)
        
        self.logger.info(f"🚀 Starting download of {len(titles)} titles...")
        self.logger.info(f"Output directory: {self.config.output_dir}")
        self.logger.info(f"Quality: {self.config.quality}")
        self.logger.info(f"Media types: {', '.join(self.config.media_types)}")
        
        for i, title in enumerate(titles, 1):
            self.logger.info(f"[{i}/{len(titles)}] Processing: {title}")
            self.download_poster(title)
            
            # Rate limiting
            if i < len(titles):
                time.sleep(self.config.delay)
        
        self.print_summary()
        
        if self.config.zip_output:
            self.create_zip()
    
    def print_summary(self):
        """Print download summary."""
        print("\n" + "="*60)
        print("📊 DOWNLOAD SUMMARY")
        print("="*60)
        print(f"Total titles: {self.stats['total']}")
        print(f"✅ Successful: {self.stats['successful']}")
        print(f"⏭️ Skipped: {self.stats['skipped']}")
        print(f"❌ Failed: {self.stats['failed']}")
        
        if self.stats["failed_titles"]:
            print(f"\nFailed titles:")
            for title in self.stats["failed_titles"]:
                print(f"  - {title}")
            
            # Save failed titles to file
            failed_file = Path(self.config.output_dir) / "failed_downloads.txt"
            with open(failed_file, "w", encoding="utf-8") as f:
                f.write("Failed Downloads\n")
                f.write("================\n\n")
                for title in self.stats["failed_titles"]:
                    f.write(f"{title}\n")
            print(f"\n📝 Failed titles saved to: {failed_file}")
    
    def create_zip(self):
        """Create zip file with all downloaded posters."""
        try:
            output_dir = Path(self.config.output_dir)
            zip_path = output_dir.parent / f"{output_dir.name}_posters.zip"
            
            poster_files = list(output_dir.glob("*.jpg"))
            
            if not poster_files:
                self.logger.warning("❌ No poster files found to zip!")
                return
            
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for poster_file in poster_files:
                    zipf.write(poster_file, poster_file.name)
            
            self.logger.info(f"📦 Created zip file: {zip_path} ({len(poster_files)} files)")
            
        except Exception as e:
            self.logger.error(f"⚠️ Error creating zip file: {e}")

def load_config_from_file(config_file: str) -> Config:
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        return Config(**config_data)
    except Exception as e:
        print(f"Error loading config file: {e}")
        return Config()

def create_sample_config():
    """Create a sample configuration file."""
    sample_config = Config()
    sample_config.api_key = "YOUR_TMDB_API_KEY"
    
    with open("config_sample.json", "w") as f:
        json.dump(asdict(sample_config), f, indent=2)
    
    print("📄 Sample configuration file created: config_sample.json")
    print("Edit this file with your settings and rename to config.json")

def main():
    parser = argparse.ArgumentParser(
        description="Universal Media Poster Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file shows.txt --quality high --output-dir my_posters
  %(prog)s --interactive --media-types tv --language ja-JP
  %(prog)s --bulk "Breaking Bad,The Office,Friends" --no-zip
  %(prog)s --config my_config.json --file shows.txt
        """
    )
    
    # Input methods (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", "-f", help="Input file (txt, csv, json)")
    input_group.add_argument("--interactive", "-i", action="store_true", help="Interactive input mode")
    input_group.add_argument("--bulk", "-b", help="Comma-separated list of titles")
    
    # Configuration
    parser.add_argument("--config", "-c", help="Configuration file (JSON)")
    parser.add_argument("--api-key", help="TMDB API key")
    parser.add_argument("--output-dir", "-o", default="posters", help="Output directory")
    parser.add_argument("--language", "-l", default="en-US", help="Language code")
    parser.add_argument("--quality", "-q", choices=["original", "high", "medium", "low"], 
                       default="original", help="Image quality")
    parser.add_argument("--media-types", nargs="+", choices=["tv", "movie"], 
                       default=["tv", "movie"], help="Media types to search")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retry attempts")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--no-zip", action="store_true", help="Don't create zip file")
    parser.add_argument("--no-metadata", action="store_true", help="Don't save metadata")
    
    # Utility commands
    parser.add_argument("--create-config", action="store_true", help="Create sample config file")
    
    args = parser.parse_args()
    
    if args.create_config:
        create_sample_config()
        return
    
    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
    else:
        config = Config()
    
    # Override config with command line arguments
    if args.api_key:
        config.api_key = args.api_key
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.language:
        config.language = args.language
    if args.quality:
        config.quality = args.quality
    if args.media_types:
        config.media_types = args.media_types
    if args.delay:
        config.delay = args.delay
    if args.max_retries:
        config.max_retries = args.max_retries
    if args.overwrite:
        config.overwrite_existing = True
    if args.no_zip:
        config.zip_output = False
    if args.no_metadata:
        config.save_metadata = False
    
    # Validate API key
    if not config.api_key or config.api_key == "YOUR_TMDB_API_KEY":
        print("❌ Please provide a valid TMDB API key!")
        print("Get one free at: https://www.themoviedb.org/settings/api")
        print("Use --api-key argument or set it in config file")
        sys.exit(1)
    
    # Initialize downloader
    downloader = UniversalPosterDownloader(config)
    
    # Get titles based on input method
    try:
        if args.file:
            titles = downloader.load_titles_from_file(args.file)
        elif args.interactive:
            titles = downloader.interactive_input()
        elif args.bulk:
            titles = [title.strip() for title in args.bulk.split(",")]
        
        if not titles:
            print("❌ No titles to process!")
            sys.exit(1)
        
        # Start downloading
        downloader.download_all(titles)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()