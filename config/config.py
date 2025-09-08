# ==============================================================================
# FILE: config/config.py
# ==============================================================================

import json
import os
from pathlib import Path
from typing import Dict, Any

# Ensure src is in the path for module resolution
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.data_models import DownloadConfig, MediaType, Quality

class ConfigManager:
    """Manages loading, saving, and merging of configuration settings."""

    DEFAULT_CONFIG_PATH = Path("config/default_config.json")
    USER_CONFIG_PATH = Path("config/user_config.json")

    @staticmethod
    def load_default_config() -> DownloadConfig:
        """Loads the default configuration, creating it if it doesn't exist."""
        if not ConfigManager.DEFAULT_CONFIG_PATH.exists():
            default_config = DownloadConfig()
            ConfigManager.save_to_file(default_config, ConfigManager.DEFAULT_CONFIG_PATH)
        
        return ConfigManager.load_from_file(ConfigManager.DEFAULT_CONFIG_PATH)

    @staticmethod
    def load_from_file(config_path: Path) -> DownloadConfig:
        """Loads configuration from a JSON file."""
        if not config_path.exists():
            print(f"Warning: Configuration file not found at {config_path}")
            return DownloadConfig()
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert string representations back to Enum members
            if 'quality' in data:
                data['quality'] = Quality(data['quality'])
            if 'media_types' in data:
                data['media_types'] = [MediaType(mt) for mt in data['media_types']]

            return DownloadConfig(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"Error loading configuration from {config_path}: {e}")
            print("Falling back to default configuration.")
            return DownloadConfig()

    @staticmethod
    def save_to_file(config: DownloadConfig, config_path: Path):
        """Saves a configuration object to a JSON file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=4)

    @staticmethod
    def create_user_config_template():
        """Creates a user-friendly configuration template with comments."""
        if ConfigManager.USER_CONFIG_PATH.exists():
            print(f"ℹ️ User config already exists at: {ConfigManager.USER_CONFIG_PATH}")
            return

        user_config_template = {
            "api_key": "YOUR_TMDB_API_KEY_HERE",
            "output_dir": "output/posters",
            "language": "en-US",
            "quality": "original",
            "media_types": ["tv", "movie"],
            "save_metadata": True,
            "zip_output": True,
            "overwrite_existing": False
        }
        
        ConfigManager.USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ConfigManager.USER_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(user_config_template, f, indent=4)
        
        print(f"✅ Created user config template at: {ConfigManager.USER_CONFIG_PATH}")
        print("Please edit it to add your TMDB API key.")