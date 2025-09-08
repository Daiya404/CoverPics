# ==============================================================================
# FILE: src/models/data_models.py
# ==============================================================================

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum

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
class DownloadConfig:
    """Configuration settings for the poster downloader."""
    api_key: str = ""
    output_dir: str = "output/posters"
    language: str = "en-US"
    delay: float = 0.5
    quality: Quality = Quality.ORIGINAL
    media_types: List[MediaType] = field(default_factory=lambda: [MediaType.TV, MediaType.MOVIE])
    max_retries: int = 3
    zip_output: bool = True
    save_metadata: bool = True
    overwrite_existing: bool = False
    backup_languages: List[str] = field(default_factory=lambda: ["en", "ja", "es"])
    log_level: str = "INFO"

    def to_dict(self) -> Dict[str, Any]:
        """Converts the configuration to a dictionary for JSON serialization."""
        result = asdict(self)
        result['quality'] = self.quality.value
        result['media_types'] = [mt.value for mt in self.media_types]
        return result

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
class DownloadResult:
    """Stores the result of a single download attempt."""
    title: str
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    media_info: Optional[MediaInfo] = None
    attempts: int = 1

@dataclass
class DownloadStats:
    """Keeps track of statistics for a download session."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    failed_titles: List[str] = field(default_factory=list)