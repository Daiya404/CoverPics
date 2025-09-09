@echo off
echo =========================================
echo    Poster Downloader v2.0 Installer
echo =========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.7+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found. Checking version...
python -c "import sys; exit(0 if sys.version_info >= (3,7) else 1)" 2>nul
if errorlevel 1 (
    echo ERROR: Python 3.7 or higher is required.
    echo Please update your Python installation.
    pause
    exit /b 1
)

echo ✓ Python version is compatible

REM Install requirements
echo.
echo Installing required packages...
python -m pip install requests --user
if errorlevel 1 (
    echo WARNING: Failed to install requests package.
    echo You may need to install it manually: pip install requests
    pause
)

echo ✓ Dependencies installed

REM Create sample files
echo.
echo Creating sample files...
mkdir data 2>nul
mkdir posters 2>nul

REM Create sample titles file
(
echo Breaking Bad
echo The Mandalorian  
echo Interstellar
echo Parasite ^(2019^)
echo Game of Thrones
) > data\sample_titles.txt

echo ✓ Sample files created

echo.
echo =========================================
echo    Installation Complete!
echo =========================================
echo.
echo To run the Poster Downloader:
echo   1. Double-click poster_downloader_gui.py
echo   2. Or run: python poster_downloader_gui.py
echo.
echo Don't forget to get your free TMDB API key:
echo https://www.themoviedb.org/settings/api
echo.
echo Sample titles file created in: data\sample_titles.txt
echo Posters will be saved to: posters\
echo.
pause