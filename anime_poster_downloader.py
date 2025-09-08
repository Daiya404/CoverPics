import os
import requests
import zipfile
import time
from urllib.parse import quote

# ==== CONFIGURATION ====
API_KEY = "461a144e9462f5e3707d25318ce20ddc"  # get it free from https://www.themoviedb.org/settings/api
OUTPUT_DIR = "anime_tv_posters"
ZIP_NAME = "all_anime_tv_posters.zip"
LANGUAGE = "en-US"
DELAY_BETWEEN_REQUESTS = 0.5  # seconds to avoid rate limiting

# List of all shows from your image
SHOWS = [
    "Kochikame",
    "Takeshi's Castle",
    "Shaka laka boom boom",
    "Junior G",
    "Recess",
    "Foster's home for imaginary friends",
    "Shinchan",
    "Hageman",
    "Perman",
    "Ninja Hattori",
    "Kiteretsu",
    "Shaolin showdown",
    "Shaun the sheep",
    "Kids next door",
    "Courage the cowardly dog",
    "Pokemon",
    "Digimon",
    "Naruto",
    "Fairy tail",
    "Dragon ball Z",
    "Jackie chan adventures",
    "Inazuma eleven",
    "Speed",
    "Beyblade",
    "Galactic football",
    "Spongebob",
    "Power rangers",
    "Scooby doo",
    "Looney tunes",
    "Mickey",
    "Popeye",
    "Billy mandy aur life me haddi",
    "Samurai jack",
    "Teen titans",
    "Dexter",
    "Powerpuff girls",
    "Winx club",
    "Johnny bravo",
    "Ed edd and eddy",
    "My gym partners monkey",
    "Chowder",
    "Ben ten",
    "Tom and jerry",
    "Justice league",
    "Camp lazlo",
    "Johnny test",
    "Drake and josh",
    "Oswald",
    "Noddy",
    "Thomas and friends",
    "Bob the builder",
    "Pingu",
    "Teletubbies",
    "Oggy and the cockroaches",
    "Postman pat",
    "Batman",
    "Spiderman",
    "Talespin",
    "Ultimate spiderman",
    "Ozzy and drix",
    "Spiderman and friends",
    "Tarzan",
    "Doraemon",
    "Phineas and ferb",
    "Kid vs kat",
    "Timon and pumba",
    "Suite life of zack and cody",
    "American dragon",
    "Blues clues",
    "Art attack",
    "MAD",
    "Little krishna",
    "Zorro",
    "Detective conan",
    "Pink panther",
    "Dragon tales",
    "Simba",
    "Captain planet",
    "Shaktimaan",
    "Ninja turtles",
    "Dragon booster",
    "Goosebumps",
    "World of quest",
    "HeMan",
    "Chacha chaudhary",
    "Richie rich",
    "Tenali rama",
    "Akbar aur birbal",
    "Flintstones",
    "The land before time",
    "Vartamaan",
    "Time squad",
    "Wildcats",
    "Swat cats",
    "Yu gi oh",
    "Krish trish and baltiboy",
    "Denver",
    "Dennis the menace",
    "Kinnikuman muscle man",
    "SRMTHFG",
    "Roll no 21",
    "Bakugan",
    "Wizards of waverly place",
    "Panchatantra",
    "Franklin and friends",
    "Monster buster club",
    "Duel masters"
]

# ==== SCRIPT ====
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/original"  # highest quality

def get_poster_url(title):
    """Get the poster URL for a given show title, checking both TV and movie endpoints."""
    # First try TV shows
    search_url = f"{BASE_URL}/search/tv"
    params = {"api_key": API_KEY, "query": title, "language": LANGUAGE}
    
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if results:
            poster_path = results[0].get("poster_path")
            if poster_path:
                return IMG_BASE + poster_path, "TV"
        
        # If not found in TV, try movies
        search_url = f"{BASE_URL}/search/movie"
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if results:
            poster_path = results[0].get("poster_path")
            if poster_path:
                return IMG_BASE + poster_path, "Movie"
                
        return None, None
        
    except requests.RequestException as e:
        print(f"⚠️ Error searching for {title}: {e}")
        return None, None

def sanitize_filename(filename):
    """Create a safe filename by replacing problematic characters."""
    # Replace problematic characters with underscores
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_"
    sanitized = "".join(c if c in safe_chars else "_" for c in filename)
    # Replace multiple spaces/underscores with single underscore
    sanitized = "_".join(sanitized.split())
    return sanitized.replace(" ", "_")

def download_posters(shows):
    """Download posters for all shows in the list."""
    successful_downloads = 0
    failed_downloads = []
    
    print(f"📺 Starting download of {len(shows)} show posters...\n")
    
    for i, show in enumerate(shows, 1):
        print(f"[{i}/{len(shows)}] Fetching poster for: {show}")
        
        url, media_type = get_poster_url(show)
        
        if not url:
            print(f"❌ Poster not found for {show}")
            failed_downloads.append(show)
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            img_data = response.content
            
            # Create safe filename
            safe_filename = sanitize_filename(show)
            file_path = os.path.join(OUTPUT_DIR, f"{safe_filename}.jpg")
            
            with open(file_path, "wb") as f:
                f.write(img_data)
            
            print(f"✅ Saved {file_path} ({media_type})")
            successful_downloads += 1
            
        except Exception as e:
            print(f"⚠️ Error downloading {show}: {e}")
            failed_downloads.append(show)
        
        # Add delay to be respectful to the API
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print(f"\n📊 Download Summary:")
    print(f"✅ Successful: {successful_downloads}")
    print(f"❌ Failed: {len(failed_downloads)}")
    
    if failed_downloads:
        print(f"\nFailed downloads:")
        for show in failed_downloads:
            print(f"  - {show}")

def zip_posters():
    """Create a zip file containing all downloaded posters."""
    try:
        poster_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.jpg')]
        
        if not poster_files:
            print("❌ No posters found to zip!")
            return
        
        with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in poster_files:
                file_path = os.path.join(OUTPUT_DIR, file)
                zipf.write(file_path, file)
        
        print(f"\n🎉 {len(poster_files)} posters zipped into {ZIP_NAME}")
        
    except Exception as e:
        print(f"⚠️ Error creating zip file: {e}")

def create_failed_list(failed_shows):
    """Create a text file with shows that failed to download."""
    if failed_shows:
        with open("failed_downloads.txt", "w", encoding="utf-8") as f:
            f.write("Shows that failed to download:\n")
            f.write("=" * 40 + "\n")
            for show in failed_shows:
                f.write(f"{show}\n")
        print(f"📝 Failed downloads list saved to failed_downloads.txt")

if __name__ == "__main__":
    # Check if API key is set
    if API_KEY == "YOUR_TMDB_API_KEY":
        print("❌ Please set your TMDB API key in the script!")
        print("Get one free at: https://www.themoviedb.org/settings/api")
        print("Replace 'YOUR_TMDB_API_KEY' with your actual API key.")
        exit(1)
    
    print("🎬 Anime & TV Show Poster Downloader")
    print("=" * 50)
    print(f"Total shows to download: {len(SHOWS)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Delay between requests: {DELAY_BETWEEN_REQUESTS}s")
    print("=" * 50)
    
    # Download all posters
    download_posters(SHOWS)
    
    # Create zip file
    zip_posters()
    
    print(f"\n🏁 Script completed! Check the '{OUTPUT_DIR}' folder for individual posters.")
    print(f"📦 All posters are also available in '{ZIP_NAME}'")