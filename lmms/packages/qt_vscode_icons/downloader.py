import os
import zipfile
import requests
import json
import shutil
from pathlib import Path

def get_assets_dir():
    return Path(__file__).parent / "assets"

def download_and_extract_icons(force=False):
    assets_dir = get_assets_dir()
    icons_dir = assets_dir / "icons"
    json_path = assets_dir / "material-icons.json"
    
    if icons_dir.exists() and json_path.exists() and not force:
        # Already downloaded
        return True
        
    print("Downloading VS Code Material Icon Theme from Marketplace...")
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # URL for the VSIX package from Visual Studio Marketplace
    url = "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/PKief/vsextensions/material-icon-theme/latest/vspackage"
    
    vsix_path = assets_dir / "theme.vsix"
    
    try:
        # Download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(vsix_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print("Extracting icons...")
        # VSIX is just a ZIP file
        with zipfile.ZipFile(vsix_path, 'r') as zip_ref:
            # We need to extract the extension/icons directory and the extension/dist/material-icons.json
            for member in zip_ref.namelist():
                if member.startswith('extension/icons/') and member.endswith('.svg'):
                    # Save SVG to assets_dir/icons/
                    filename = Path(member).name
                    source = zip_ref.open(member)
                    
                    icons_dir.mkdir(exist_ok=True)
                    target_path = icons_dir / filename
                    with open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                        
                elif member == 'extension/dist/material-icons.json':
                    # Save JSON mapping
                    source = zip_ref.open(member)
                    with open(json_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                        
        print("Icons successfully downloaded and extracted.")
        return True
        
    except Exception as e:
        print(f"Failed to download icons: {e}")
        return False
    finally:
        if vsix_path.exists():
            vsix_path.unlink()

if __name__ == "__main__":
    download_and_extract_icons()
