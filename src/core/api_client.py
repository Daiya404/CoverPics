# ==============================================================================
# FILE: src/core/api_client.py
# ==============================================================================

import logging
import time
import requests
from typing import Optional, List, Dict, Any

# Ensure src modules can be imported
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.data_models import MediaInfo, MediaType, DownloadConfig
from src.utils.logging_config import LOGGER_NAME

class TMDBApiClient:
    """
    A robust client for The Movie Database (TMDB) API.

    This class encapsulates all network-related logic, including:
    - Making authenticated API requests using an efficient session object.
    - Enforcing a polite rate limit to avoid overwhelming the API.
    - Handling common network errors (timeouts, connection issues, HTTP errors).
    - Parsing API JSON responses into clean, application-specific data models.
    """

    BASE_URL = "https://api.themoviedb.org/3"
    IMG_BASE_URL = "https://image.tmdb.org/t/p"

    def __init__(self, config: DownloadConfig):
        """
        Initializes the TMDB API client.

        Args:
            config: The application's configuration settings.
        """
        self.config = config
        self.logger = logging.getLogger(LOGGER_NAME)
        
        # Using a requests.Session allows for connection pooling, which is more efficient
        # for making multiple requests to the same host.
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OptimizedPosterDownloader/1.1',
            'Accept': 'application/json'
        })
        
        # Use time.monotonic() for rate limiting, as it's not affected by system time changes.
        self._last_request_time: float = 0.0

    def _apply_rate_limit(self) -> None:
        """Prevents sending requests faster than the configured delay."""
        time_since_last = time.monotonic() - self._last_request_time
        if time_since_last < self.config.delay:
            time.sleep(self.config.delay - time_since_last)
        self._last_request_time = time.monotonic()

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes a GET request and handles all potential network errors.

        Args:
            endpoint: The API endpoint path (e.g., "search/movie").
            params: A dictionary of query parameters.

        Returns:
            The JSON response as a dictionary, or None if any error occurs.
        """
        self._apply_rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        full_params = params.copy()
        full_params['api_key'] = self.config.api_key
        
        try:
            response = self.session.get(url, params=full_params, timeout=15)
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
            return response.json()
        
        except requests.exceptions.Timeout:
            self.logger.error(f"Request timed out while connecting to {url}")
        except requests.exceptions.HTTPError as err:
            # The API often returns JSON with an error message, which is useful to log.
            error_details = err.response.json().get('status_message', err)
            self.logger.error(f"HTTP Error {err.response.status_code} for {url}: {error_details}")
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Connection error. Failed to establish a connection to {url}")
        except requests.exceptions.RequestException as err:
            self.logger.error(f"An unexpected request error occurred: {err}")
            
        return None

    def search_media(self, title: str, media_type: MediaType, language: str) -> List[MediaInfo]:
        """
        Searches for media by title and safely parses the results.

        Args:
            title: The search term (e.g., "The Matrix").
            media_type: The type of media to search for (TV or MOVIE).
            language: The language code for the search (e.g., 'en-US').

        Returns:
            A list of MediaInfo objects, sorted by popularity. Returns an
            empty list if the search fails or yields no valid results.
        """
        endpoint = f"search/{media_type.value}"
        params = {'query': title, 'language': language}
        
        self.logger.debug(f"Searching for {media_type.value}: '{title}' in language '{language}'")
        response_data = self._make_request(endpoint, params)
        
        if not response_data or not response_data.get('results'):
            self.logger.warning(f"No results found for '{title}' as a {media_type.value}.")
            return []

        parsed_results = []
        for item in response_data['results']:
            # Use .get() for all fields to prevent KeyErrors if the API response is malformed.
            # A result is only considered valid if it has an ID.
            if not isinstance(item, dict) or 'id' not in item:
                continue

            try:
                # Differentiate keys based on media type
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
            except (TypeError, ValueError) as e:
                self.logger.warning(f"Could not parse a search result for '{title}'. Data: {item}. Error: {e}")
        
        # Sort results by popularity to increase the chance of finding the correct match first.
        return sorted(parsed_results, key=lambda x: x.popularity, reverse=True)

    def get_poster_url(self, poster_path: Optional[str]) -> Optional[str]:
        """
        Constructs the full, downloadable URL for a poster image.

        Args:
            poster_path: The relative path from the API response (e.g., "/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg").

        Returns:
            The complete URL, or None if the poster_path is missing.
        """
        if not poster_path:
            return None
            
        quality = self.config.quality.value
        return f"{self.IMG_BASE_URL}/{quality}{poster_path}"