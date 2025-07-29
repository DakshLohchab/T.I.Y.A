import os
import requests
import shutil

# Direct links to Orbitron TTF files from Google Fonts GitHub repo
FONT_URLS = [
    "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron-Black.ttf",
    "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron-Bold.ttf",
    "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron-Medium.ttf",
    "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron-Regular.ttf",
    "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron-SemiBold.ttf"
]

def install_fonts():
    try:
        font_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
        for url in FONT_URLS:
            font_name = url.split('/')[-1]
            print(f"Downloading {font_name}...")
            
            response = requests.get(url, stream=True)
            dest_path = os.path.join(font_dir, font_name)
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Installed: {font_name}")
        
        print("All fonts installed successfully!")
        return True
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    install_fonts()