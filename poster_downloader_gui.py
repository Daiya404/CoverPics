#!/usr/bin/env python3
"""
Enhanced Poster Downloader with GUI Interface
A user-friendly application to download movie and TV show posters from TMDB
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
import requests
from dataclasses import dataclass, field
from enum import Enum
import zipfile
import re
import unicodedata

# ============================================================================
# DATA MODELS
# ============================================================================

class MediaType(Enum):
    """Enum for media types supported by TMDB."""
    TV = "tv"
    MOVIE = "movie"

class Quality(Enum):
    """Enum for poster image quality."""
    ORIGINAL = "original"
    HIGH = "w500"
    MEDIUM = "w342" 
    LOW = "w185"

@dataclass
class MediaInfo:
    """Represents information about a media item from the TMDB API."""
    id: int
    title: str
    original_title: str
    poster_path: Optional[str]
    overview: str
    release_date: str
    media_type: MediaType
    language: str
    popularity: float
    vote_average: float

@dataclass
class DownloadConfig:
    """Configuration settings for the poster downloader."""
    api_key: str = ""
    output_dir: str = "posters"
    language: str = "en-US"
    delay: float = 0.5
    quality: Quality = Quality.ORIGINAL
    media_types: List[MediaType] = field(default_factory=lambda: [MediaType.TV, MediaType.MOVIE])
    max_retries: int = 3
    zip_output: bool = True
    save_metadata: bool = True
    overwrite_existing: bool = False
    backup_languages: List[str] = field(default_factory=lambda: ["en", "ja", "es"])

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """Cleans and sanitizes a string to be a valid filename."""
    if not isinstance(filename, str) or not filename.strip():
        return "untitled"
    
    # Normalize Unicode to ASCII
    sanitized = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    
    # Replace illegal characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', sanitized)
    sanitized = re.sub(r'__+', '_', sanitized)
    sanitized = sanitized.strip('_-')
    sanitized = sanitized[:max_length]
    
    return sanitized or "untitled"

def format_file_size(size_bytes: int) -> str:
    """Converts bytes to human-readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB")
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float /= 1024.0
        i += 1
    return f"{size_float:.1f}{size_names[i]}"

def validate_api_key(api_key: str) -> bool:
    """Validates TMDB API key format."""
    if not isinstance(api_key, str):
        return False
    pattern = r'^[a-zA-Z0-9]{32}$'
    return bool(re.match(pattern, api_key))

# ============================================================================
# TMDB API CLIENT
# ============================================================================

class TMDBApiClient:
    """Client for The Movie Database (TMDB) API."""
    
    BASE_URL = "https://api.themoviedb.org/3"
    IMG_BASE_URL = "https://image.tmdb.org/t/p"
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PosterDownloader/2.0',
            'Accept': 'application/json'
        })
        self._last_request_time = 0.0
    
    def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        time_since_last = time.time() - self._last_request_time
        if time_since_last < self.config.delay:
            time.sleep(self.config.delay - time_since_last)
        self._last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a GET request to the TMDB API."""
        self._apply_rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        full_params = params.copy()
        full_params['api_key'] = self.config.api_key
        
        try:
            response = self.session.get(url, params=full_params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API request failed: {e}")
            return None
    
    def search_media(self, title: str, media_type: MediaType, language: str) -> List[MediaInfo]:
        """Search for media by title."""
        endpoint = f"search/{media_type.value}"
        params = {'query': title, 'language': language}
        
        response_data = self._make_request(endpoint, params)
        if not response_data or not response_data.get('results'):
            return []
        
        parsed_results = []
        for item in response_data['results']:
            if not isinstance(item, dict) or 'id' not in item:
                continue
            
            try:
                title_key = 'name' if media_type == MediaType.TV else 'title'
                original_title_key = 'original_name' if media_type == MediaType.TV else 'original_title'
                release_date_key = 'first_air_date' if media_type == MediaType.TV else 'release_date'
                
                media_info = MediaInfo(
                    id=item['id'],
                    title=item.get(title_key, "Title not available"),
                    original_title=item.get(original_title_key, "N/A"),
                    poster_path=item.get('poster_path'),
                    overview=item.get('overview', ""),
                    release_date=item.get(release_date_key, ""),
                    media_type=media_type,
                    language=language,
                    popularity=float(item.get('popularity', 0.0)),
                    vote_average=float(item.get('vote_average', 0.0))
                )
                parsed_results.append(media_info)
            except Exception as e:
                print(f"Error parsing result: {e}")
                continue
        
        return sorted(parsed_results, key=lambda x: x.popularity, reverse=True)
    
    def get_poster_url(self, poster_path: Optional[str]) -> Optional[str]:
        """Get full poster URL."""
        if not poster_path:
            return None
        quality = self.config.quality.value
        return f"{self.IMG_BASE_URL}/{quality}{poster_path}"

# ============================================================================
# POSTER DOWNLOADER
# ============================================================================

class PosterDownloader:
    """Main poster downloader class."""
    
    def __init__(self, config: DownloadConfig, progress_callback=None, log_callback=None):
        self.config = config
        self.api_client = TMDBApiClient(config)
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        
        # Create output directory
        self.output_path = Path(self.config.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Stats
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'failed_titles': []
        }
    
    def log(self, message: str):
        """Log a message."""
        print(message)
        if self.log_callback:
            self.log_callback(message)
    
    def update_progress(self, current: int, total: int):
        """Update progress."""
        if self.progress_callback:
            self.progress_callback(current, total)
    
    def _find_best_match(self, title: str) -> Optional[MediaInfo]:
        """Find the best match for a title."""
        self.log(f"Searching for: {title}")
        
        # Search primary language first
        for media_type in self.config.media_types:
            results = self.api_client.search_media(title, media_type, self.config.language)
            if results:
                best_result = results[0]
                self.log(f"Found: {best_result.title} ({best_result.media_type.value})")
                return best_result
        
        # Try backup languages
        for lang in self.config.backup_languages:
            for media_type in self.config.media_types:
                results = self.api_client.search_media(title, media_type, lang)
                if results:
                    best_result = results[0]
                    self.log(f"Found in {lang}: {best_result.title}")
                    return best_result
        
        self.log(f"No match found for: {title}")
        return None
    
    def download_single_poster(self, title: str) -> bool:
        """Download a single poster."""
        safe_filename = sanitize_filename(title)
        poster_filepath = self.output_path / f"{safe_filename}.jpg"
        
        # Check if already exists
        if not self.config.overwrite_existing and poster_filepath.exists():
            self.log(f"Skipping (already exists): {title}")
            self.stats['skipped'] += 1
            return True
        
        # Find media
        media_info = self._find_best_match(title)
        if not media_info or not media_info.poster_path:
            self.log(f"Failed: No poster found for {title}")
            self.stats['failed'] += 1
            self.stats['failed_titles'].append(title)
            return False
        
        # Get poster URL
        poster_url = self.api_client.get_poster_url(media_info.poster_path)
        if not poster_url:
            self.log(f"Failed: Could not get poster URL for {title}")
            self.stats['failed'] += 1
            self.stats['failed_titles'].append(title)
            return False
        
        # Download poster
        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = requests.get(poster_url, stream=True, timeout=30)
                response.raise_for_status()
                
                with poster_filepath.open('wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size = format_file_size(poster_filepath.stat().st_size)
                self.log(f"Downloaded: {title} ({file_size})")
                
                # Save metadata
                if self.config.save_metadata:
                    self._save_metadata(safe_filename, media_info, poster_url)
                
                self.stats['successful'] += 1
                return True
                
            except Exception as e:
                self.log(f"Attempt {attempt} failed for {title}: {e}")
                if attempt < self.config.max_retries:
                    time.sleep(1)
                else:
                    self.stats['failed'] += 1
                    self.stats['failed_titles'].append(title)
                    return False
        
        return False
    
    def _save_metadata(self, safe_filename: str, media_info: MediaInfo, poster_url: str):
        """Save metadata for downloaded poster."""
        metadata = {
            "title": media_info.title,
            "original_title": media_info.original_title,
            "media_type": media_info.media_type.value,
            "release_date": media_info.release_date,
            "overview": media_info.overview,
            "vote_average": media_info.vote_average,
            "poster_url": poster_url,
            "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        metadata_path = self.output_path / f"{safe_filename}_metadata.json"
        try:
            with metadata_path.open('w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"Failed to save metadata: {e}")
    
    def download_from_list(self, titles: List[str]):
        """Download posters for a list of titles."""
        self.stats = {
            'total': len(titles),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'failed_titles': []
        }
        
        self.log(f"Starting download of {len(titles)} titles...")
        
        for i, title in enumerate(titles, 1):
            self.log(f"[{i}/{len(titles)}] Processing: {title}")
            self.download_single_poster(title)
            self.update_progress(i, len(titles))
        
        self.log(f"\nDownload complete!")
        self.log(f"Successful: {self.stats['successful']}")
        self.log(f"Skipped: {self.stats['skipped']}")
        self.log(f"Failed: {self.stats['failed']}")
        
        # Create ZIP if requested
        if self.config.zip_output and self.stats['successful'] > 0:
            self._create_zip()
        
        # Save failed titles
        if self.stats['failed_titles']:
            self._save_failed_titles()
    
    def _create_zip(self):
        """Create ZIP archive of downloaded posters."""
        try:
            zip_path = self.output_path.parent / f"{self.output_path.name}.zip"
            poster_files = list(self.output_path.glob("*.jpg"))
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in poster_files:
                    zipf.write(file, file.name)
            
            zip_size = format_file_size(zip_path.stat().st_size)
            self.log(f"Created ZIP archive: {zip_path.name} ({zip_size})")
        except Exception as e:
            self.log(f"Failed to create ZIP: {e}")
    
    def _save_failed_titles(self):
        """Save list of failed titles."""
        try:
            failed_path = self.output_path / "failed_downloads.txt"
            with failed_path.open('w', encoding='utf-8') as f:
                f.write("Failed Downloads\n")
                f.write("================\n\n")
                for title in self.stats['failed_titles']:
                    f.write(f"- {title}\n")
            self.log(f"Saved failed titles to: {failed_path.name}")
        except Exception as e:
            self.log(f"Failed to save failed titles: {e}")

# ============================================================================
# GUI APPLICATION
# ============================================================================

class PosterDownloaderGUI:
    """GUI application for the poster downloader."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Poster Downloader v2.0")
        self.root.geometry("800x700")
        self.root.minsize(600, 500)
        
        # Configuration
        self.config = DownloadConfig()
        self.load_config()
        
        # Variables
        self.is_downloading = False
        
        # Setup UI
        self.setup_ui()
        
        # Load saved settings
        self.load_settings_to_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Download tab
        download_frame = ttk.Frame(notebook)
        notebook.add(download_frame, text="Download")
        self.setup_download_tab(download_frame)
        
        # Settings tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        self.setup_settings_tab(settings_frame)
        
        # About tab
        about_frame = ttk.Frame(notebook)
        notebook.add(about_frame, text="About")
        self.setup_about_tab(about_frame)
    
    def setup_download_tab(self, parent):
        """Setup the download tab."""
        # Title input section
        title_frame = ttk.LabelFrame(parent, text="Add Titles", padding=10)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(title_frame, text="Enter title:").pack(anchor=tk.W)
        self.title_entry = ttk.Entry(title_frame, width=50)
        self.title_entry.pack(fill=tk.X, pady=(0, 5))
        self.title_entry.bind('<Return>', self.add_title)
        
        title_buttons = ttk.Frame(title_frame)
        title_buttons.pack(fill=tk.X)
        
        ttk.Button(title_buttons, text="Add Title", command=self.add_title).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(title_buttons, text="Load from File", command=self.load_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(title_buttons, text="Clear All", command=self.clear_titles).pack(side=tk.LEFT, padx=5)
        
        # Titles list
        list_frame = ttk.LabelFrame(parent, text="Titles to Download", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.titles_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar.set)
        self.titles_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.titles_listbox.yview)
        
        # List buttons
        list_buttons = ttk.Frame(list_frame)
        list_buttons.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(list_buttons, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT)
        
        # Progress section
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding=10)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(anchor=tk.W)
        
        # Download button
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.download_button = ttk.Button(button_frame, text="Start Download", command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_download, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
        
        # Log output
        log_frame = ttk.LabelFrame(parent, text="Log", padding=5)
        log_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def setup_settings_tab(self, parent):
        """Setup the settings tab."""
        # Create main frame with scrollbar
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # API Key section
        api_frame = ttk.LabelFrame(scrollable_frame, text="TMDB API Settings", padding=10)
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(api_frame, text="API Key:").pack(anchor=tk.W)
        self.api_key_entry = ttk.Entry(api_frame, width=40, show="*")
        self.api_key_entry.pack(fill=tk.X, pady=(0, 5))
        
        api_buttons = ttk.Frame(api_frame)
        api_buttons.pack(fill=tk.X)
        ttk.Button(api_buttons, text="Get API Key", command=self.open_tmdb_signup).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(api_buttons, text="Test API Key", command=self.test_api_key).pack(side=tk.LEFT)
        
        # Output settings
        output_frame = ttk.LabelFrame(scrollable_frame, text="Output Settings", padding=10)
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(output_frame, text="Output Directory:").pack(anchor=tk.W)
        dir_frame = ttk.Frame(output_frame)
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.output_dir_var = tk.StringVar(value=self.config.output_dir)
        self.output_dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var)
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(dir_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.RIGHT)
        
        ttk.Label(output_frame, text="Quality:").pack(anchor=tk.W)
        self.quality_var = tk.StringVar(value=self.config.quality.value)
        quality_combo = ttk.Combobox(output_frame, textvariable=self.quality_var, values=[q.value for q in Quality], state="readonly")
        quality_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Download options
        options_frame = ttk.Frame(output_frame)
        options_frame.pack(fill=tk.X)
        
        self.zip_output_var = tk.BooleanVar(value=self.config.zip_output)
        ttk.Checkbutton(options_frame, text="Create ZIP archive", variable=self.zip_output_var).pack(anchor=tk.W)
        
        self.save_metadata_var = tk.BooleanVar(value=self.config.save_metadata)
        ttk.Checkbutton(options_frame, text="Save metadata", variable=self.save_metadata_var).pack(anchor=tk.W)
        
        self.overwrite_var = tk.BooleanVar(value=self.config.overwrite_existing)
        ttk.Checkbutton(options_frame, text="Overwrite existing files", variable=self.overwrite_var).pack(anchor=tk.W)
        
        # Media type settings
        media_frame = ttk.LabelFrame(scrollable_frame, text="Media Types", padding=10)
        media_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.tv_var = tk.BooleanVar(value=MediaType.TV in self.config.media_types)
        self.movie_var = tk.BooleanVar(value=MediaType.MOVIE in self.config.media_types)
        
        ttk.Checkbutton(media_frame, text="TV Shows", variable=self.tv_var).pack(anchor=tk.W)
        ttk.Checkbutton(media_frame, text="Movies", variable=self.movie_var).pack(anchor=tk.W)
        
        # Language settings
        lang_frame = ttk.LabelFrame(scrollable_frame, text="Language Settings", padding=10)
        lang_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(lang_frame, text="Primary Language:").pack(anchor=tk.W)
        self.language_var = tk.StringVar(value=self.config.language)
        ttk.Entry(lang_frame, textvariable=self.language_var, width=10).pack(anchor=tk.W, pady=(0, 10))
        
        # Advanced settings
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="Advanced Settings", padding=10)
        advanced_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(advanced_frame, text="Request Delay (seconds):").pack(anchor=tk.W)
        self.delay_var = tk.DoubleVar(value=self.config.delay)
        delay_scale = ttk.Scale(advanced_frame, from_=0.1, to=2.0, variable=self.delay_var, orient=tk.HORIZONTAL)
        delay_scale.pack(fill=tk.X, pady=(0, 5))
        self.delay_label = ttk.Label(advanced_frame, text=f"Current: {self.config.delay}s")
        self.delay_label.pack(anchor=tk.W, pady=(0, 10))
        delay_scale.configure(command=self.update_delay_label)
        
        ttk.Label(advanced_frame, text="Max Retries:").pack(anchor=tk.W)
        self.retries_var = tk.IntVar(value=self.config.max_retries)
        ttk.Spinbox(advanced_frame, from_=1, to=10, textvariable=self.retries_var, width=10).pack(anchor=tk.W)
        
        # Save settings button
        ttk.Button(scrollable_frame, text="Save Settings", command=self.save_settings).pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def setup_about_tab(self, parent):
        """Setup the about tab."""
        about_text = """
Poster Downloader v2.0

A user-friendly application to download movie and TV show posters from The Movie Database (TMDB).

Features:
• Easy-to-use graphical interface
• Support for movies and TV shows
• Multiple quality options
• Batch downloading
• Metadata saving
• ZIP archive creation
• Configurable settings

How to use:
1. Get a free API key from TMDB (https://www.themoviedb.org/settings/api)
2. Enter your API key in the Settings tab
3. Add titles to download in the Download tab
4. Click "Start Download"

Requirements:
• Python 3.7+
• Internet connection
• TMDB API key (free)

Created with ❤️ for movie and TV enthusiasts
        """
        
        text_widget = scrolledtext.ScrolledText(parent, wrap=tk.WORD, padx=20, pady=20)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, about_text)
        text_widget.config(state=tk.DISABLED)
    
    def load_config(self):
        """Load configuration from file."""
        config_path = Path("poster_downloader_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                
                # Update config with loaded data
                if 'api_key' in data:
                    self.config.api_key = data['api_key']
                if 'output_dir' in data:
                    self.config.output_dir = data['output_dir']
                if 'language' in data:
                    self.config.language = data['language']
                if 'delay' in data:
                    self.config.delay = data['delay']
                if 'quality' in data:
                    self.config.quality = Quality(data['quality'])
                if 'media_types' in data:
                    self.config.media_types = [MediaType(mt) for mt in data['media_types']]
                if 'max_retries' in data:
                    self.config.max_retries = data['max_retries']
                if 'zip_output' in data:
                    self.config.zip_output = data['zip_output']
                if 'save_metadata' in data:
                    self.config.save_metadata = data['save_metadata']
                if 'overwrite_existing' in data:
                    self.config.overwrite_existing = data['overwrite_existing']
            except Exception as e:
                print(f"Error loading config: {e}")
    
    def save_config(self):
        """Save configuration to file."""
        config_path = Path("poster_downloader_config.json")
        try:
            config_data = {
                'api_key': self.config.api_key,
                'output_dir': self.config.output_dir,
                'language': self.config.language,
                'delay': self.config.delay,
                'quality': self.config.quality.value,
                'media_types': [mt.value for mt in self.config.media_types],
                'max_retries': self.config.max_retries,
                'zip_output': self.config.zip_output,
                'save_metadata': self.config.save_metadata,
                'overwrite_existing': self.config.overwrite_existing
            }
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def load_settings_to_ui(self):
        """Load current settings to UI elements."""
        if hasattr(self, 'api_key_entry'):
            self.api_key_entry.delete(0, tk.END)
            self.api_key_entry.insert(0, self.config.api_key)
    
    def add_title(self, event=None):
        """Add a title to the download list."""
        title = self.title_entry.get().strip()
        if title:
            self.titles_listbox.insert(tk.END, title)
            self.title_entry.delete(0, tk.END)
    
    def remove_selected(self):
        """Remove selected titles from the list."""
        selected = self.titles_listbox.curselection()
        for index in reversed(selected):
            self.titles_listbox.delete(index)
    
    def clear_titles(self):
        """Clear all titles from the list."""
        if messagebox.askyesno("Confirm", "Clear all titles?"):
            self.titles_listbox.delete(0, tk.END)
    
    def load_from_file(self):
        """Load titles from a file."""
        file_path = filedialog.askopenfilename(
            title="Select file with titles",
            filetypes=[
                ("Text files", "*.txt"),
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                titles = []
                file_path = Path(file_path)
                
                if file_path.suffix.lower() == '.json':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        titles = [str(item).strip() for item in data if str(item).strip()]
                    elif isinstance(data, dict) and 'titles' in data:
                        titles = [str(item).strip() for item in data['titles'] if str(item).strip()]
                
                elif file_path.suffix.lower() == '.csv':
                    import csv
                    with open(file_path, 'r', encoding='utf-8', newline='') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if row and row[0].strip():
                                titles.append(row[0].strip())
                
                else:  # txt or other
                    with open(file_path, 'r', encoding='utf-8') as f:
                        titles = [line.strip() for line in f if line.strip()]
                
                for title in titles:
                    self.titles_listbox.insert(tk.END, title)
                
                self.log_message(f"Loaded {len(titles)} titles from {file_path.name}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
    
    def browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(title="Select output directory")
        if directory:
            self.output_dir_var.set(directory)
    
    def update_delay_label(self, value):
        """Update delay label."""
        self.delay_label.config(text=f"Current: {float(value):.1f}s")
    
    def open_tmdb_signup(self):
        """Open TMDB API signup page."""
        import webbrowser
        webbrowser.open("https://www.themoviedb.org/settings/api")
    
    def test_api_key(self):
        """Test the API key."""
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("Warning", "Please enter an API key first.")
            return
        
        if not validate_api_key(api_key):
            messagebox.showerror("Error", "Invalid API key format. Should be 32 characters long.")
            return
        
        # Test API key by making a simple request
        try:
            url = "https://api.themoviedb.org/3/configuration"
            params = {'api_key': api_key}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                messagebox.showinfo("Success", "API key is valid!")
            else:
                messagebox.showerror("Error", f"API key test failed: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to test API key: {e}")
    
    def save_settings(self):
        """Save current settings."""
        try:
            # Update config from UI
            self.config.api_key = self.api_key_entry.get().strip()
            self.config.output_dir = self.output_dir_var.get()
            self.config.language = self.language_var.get()
            self.config.delay = self.delay_var.get()
            self.config.quality = Quality(self.quality_var.get())
            self.config.max_retries = self.retries_var.get()
            self.config.zip_output = self.zip_output_var.get()
            self.config.save_metadata = self.save_metadata_var.get()
            self.config.overwrite_existing = self.overwrite_var.get()
            
            # Update media types
            media_types = []
            if self.tv_var.get():
                media_types.append(MediaType.TV)
            if self.movie_var.get():
                media_types.append(MediaType.MOVIE)
            self.config.media_types = media_types if media_types else [MediaType.TV, MediaType.MOVIE]
            
            # Save to file
            self.save_config()
            messagebox.showinfo("Success", "Settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def log_message(self, message):
        """Add a message to the log."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_progress_gui(self, current, total):
        """Update progress bar and label."""
        if total > 0:
            progress_percent = (current / total) * 100
            self.progress['value'] = progress_percent
            self.progress_label.config(text=f"Progress: {current}/{total} ({progress_percent:.1f}%)")
        self.root.update_idletasks()
    
    def start_download(self):
        """Start the download process."""
        # Validate settings
        if not self.config.api_key:
            messagebox.showerror("Error", "Please enter your TMDB API key in the Settings tab.")
            return
        
        if not validate_api_key(self.config.api_key):
            messagebox.showerror("Error", "Invalid API key format. Please check your API key.")
            return
        
        # Get titles from listbox
        titles = []
        for i in range(self.titles_listbox.size()):
            titles.append(self.titles_listbox.get(i))
        
        if not titles:
            messagebox.showwarning("Warning", "Please add some titles to download.")
            return
        
        if not self.config.media_types:
            messagebox.showerror("Error", "Please select at least one media type in Settings.")
            return
        
        # Update config from current settings
        self.save_settings()
        
        # Disable download button
        self.download_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_downloading = True
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start download in separate thread
        download_thread = threading.Thread(target=self.download_worker, args=(titles,))
        download_thread.daemon = True
        download_thread.start()
    
    def stop_download(self):
        """Stop the download process."""
        self.is_downloading = False
        self.download_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log_message("Download stopped by user.")
    
    def download_worker(self, titles):
        """Worker thread for downloading."""
        try:
            downloader = PosterDownloader(
                self.config, 
                progress_callback=self.update_progress_gui,
                log_callback=self.log_message
            )
            downloader.download_from_list(titles)
            
        except Exception as e:
            self.log_message(f"Download error: {e}")
        
        finally:
            # Re-enable download button
            self.root.after(0, self.download_finished)
    
    def download_finished(self):
        """Called when download is finished."""
        self.is_downloading = False
        self.download_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.progress_label.config(text="Download completed!")
    
    def run(self):
        """Run the application."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass

# ============================================================================
# REQUIREMENTS CHECKER
# ============================================================================

def check_requirements():
    """Check if all required packages are installed."""
    required_packages = ['requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nPlease install them using:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to run the application."""
    print("Poster Downloader v2.0")
    print("======================")
    
    # Check requirements
    if not check_requirements():
        input("Press Enter to exit...")
        return
    
    try:
        # Create and run GUI
        app = PosterDownloaderGUI()
        print("Starting GUI application...")
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()