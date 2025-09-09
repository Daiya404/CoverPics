# 🎬 Poster Downloader v2.0

A user-friendly GUI application to download high-quality movie and TV show posters from The Movie Database (TMDB).

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

## ✨ Features

- **Easy-to-use GUI**: No command line knowledge required
- **Batch downloading**: Download multiple posters at once
- **Multiple formats**: Support for movies and TV shows
- **Quality options**: Choose from various poster resolutions
- **Smart search**: Automatic fallback to backup languages
- **Metadata saving**: Save detailed information about each poster
- **ZIP archives**: Automatically create compressed archives
- **Progress tracking**: Real-time download progress
- **Error handling**: Robust error handling with retry mechanisms

## 🖼️ Screenshots

The application features a clean, tabbed interface with:

- **Download Tab**: Add titles and monitor progress
- **Settings Tab**: Configure API key, quality, and preferences
- **About Tab**: Information and usage instructions

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.7 or higher
- Internet connection
- Free TMDB API key

### 2. Installation

```bash
# Clone or download the repository
git clone https://github.com/yourusername/poster-downloader.git
cd poster-downloader

# Install dependencies
pip install -r requirements.txt

# Run the application
python poster_downloader_gui.py
```

### 3. Get Your API Key

1. Go to [TMDB API Settings](https://www.themoviedb.org/settings/api)
2. Sign up for a free account if you don't have one
3. Request an API key (it's free and instant)
4. Copy your API key

### 4. First Use

1. **Enter API Key**: Go to Settings tab and paste your TMDB API key
2. **Add Titles**: In the Download tab, type movie/TV show names
3. **Configure Settings**: Choose quality, output directory, etc.
4. **Start Download**: Click "Start Download" and watch the magic happen!

## 📋 Supported File Formats

### Input Files

- **Text files** (`.txt`): One title per line
- **JSON files** (`.json`): `["Title 1", "Title 2"]` or `{"titles": ["Title 1", "Title 2"]}`
- **CSV files** (`.csv`): Titles in the first column

### Output Files

- **Images**: High-quality JPG posters
- **Metadata**: JSON files with detailed information (optional)
- **Archives**: ZIP files containing all downloads (optional)
- **Reports**: Text files listing any failed downloads

## ⚙️ Configuration Options

### Quality Settings

- **Original**: Highest quality available
- **High** (w500): 500px width
- **Medium** (w342): 342px width
- **Low** (w185): 185px width

### Search Options

- **Media Types**: Movies, TV shows, or both
- **Languages**: Primary language with automatic fallbacks
- **Retry Logic**: Configurable retry attempts for failed downloads

### Output Options

- **Custom Directory**: Choose where to save posters
- **ZIP Creation**: Automatically create compressed archives
- **Metadata Saving**: Save detailed information about each poster
- **Overwrite Control**: Choose whether to skip existing files

## 🔧 Advanced Usage

### Batch Processing

The application supports various input methods:

```txt
# example_titles.txt
Breaking Bad
The Mandalorian
Interstellar
Parasite (2019)
```

```json
{
  "titles": ["Game of Thrones", "Chernobyl", "The Dark Knight"]
}
```

### API Rate Limiting

The application automatically handles TMDB's rate limits with configurable delays between requests (0.1-2.0 seconds).

### Error Recovery

- Automatic retries for failed downloads
- Detailed error logging
- Failed downloads list for manual retry

## 🐛 Bug Fixes in v2.0

This version fixes several issues from the original codebase:

1. **Missing Dependencies**: Fixed missing `requirements.txt` content
2. **Import Issues**: Resolved path resolution problems
3. **API Key Security**: Removed hardcoded API keys from config files
4. **Error Handling**: Added comprehensive error handling
5. **User Experience**: Complete GUI overhaul for ease of use
6. **Configuration**: Improved settings management and validation
7. **Cross-Platform**: Better compatibility across operating systems

## 🔒 Privacy & Security

- **API Key Storage**: Keys are stored locally in encrypted configuration
- **No Data Collection**: The application doesn't send any personal data
- **Local Processing**: All processing happens on your machine
- **TMDB Terms**: Respects TMDB's terms of service and rate limits

## 📝 Requirements

### System Requirements

- **OS**: Windows 7+, macOS 10.12+, or Linux
- **Python**: 3.7 or higher
- **Memory**: 256MB RAM minimum
- **Storage**: 50MB for application, variable for downloads
- **Internet**: Broadband connection recommended

### Python Dependencies

- `requests>=2.25.0`: HTTP library for API communication
- `tkinter`: GUI framework (usually included with Python)

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Bug Reports**: Open an issue with detailed reproduction steps
2. **Feature Requests**: Suggest new features or improvements
3. **Code Contributions**: Submit pull requests with your enhancements
4. **Documentation**: Help improve this README and code comments

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **TMDB**: For providing the excellent movie/TV database API
- **Python Community**: For the amazing libraries and tools
- **Contributors**: Everyone who helped improve this application

## 📞 Support

Having issues? Here's how to get help:

1. **Check the Issues**: Look for similar problems in GitHub issues
2. **Read the Docs**: Review this README carefully
3. **Create an Issue**: Open a new issue with detailed information
4. **TMDB Support**: For API-related questions, contact TMDB support

## 🔄 Changelog

### v2.0.0

- Complete GUI rewrite for user-friendliness
- Fixed all major bugs from v1.x
- Added comprehensive error handling
- Improved configuration management
- Enhanced security (no hardcoded API keys)
- Better cross-platform compatibility
- Real-time progress tracking
- Batch processing improvements

### v1.x (Original CLI Version)

- Command-line interface
- Basic downloading functionality
- Configuration file support

---

**Made with ❤️ for movie and TV enthusiasts**

_Download responsibly and respect TMDB's terms of service_
