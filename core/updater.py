import urllib.request
import json
import os
import sys
import subprocess
import zipfile
import shutil
import time

class Updater:
    """Handles checking for updates, downloading, and installing new versions."""

    REPO_URL = "https://api.github.com/repos/MustafaMahmoud-ILE/VaultPy/releases/latest"

    @staticmethod
    def check_for_updates(current_version):
        """Fetches latest release and compares versions."""
        try:
            req = urllib.request.Request(Updater.REPO_URL, headers={'User-Agent': 'VaultPy'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    latest_tag = data.get("tag_name", "v0.0.0")
                    notes = data.get("body", "No release notes provided.")
                    
                    latest_ver = latest_tag.lstrip('v')
                    current_ver = current_version.lstrip('v')
                    
                    if latest_ver > current_ver:
                        assets = data.get("assets", [])
                        download_url = None
                        for asset in assets:
                            if asset.get("name", "").endswith(".zip"):
                                download_url = asset.get("browser_download_url")
                                break
                        
                        return True, latest_tag, download_url, notes
                return False, None, None, None
        except Exception as e:
            print(f"Update check failed: {e}")
            return False, None, None, None

    @staticmethod
    def download_update(url, target_path, progress_callback=None):
        """Downloads the update ZIP with progress reporting."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'VaultPy'})
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    
                    # If size is unknown, emit a special value to trigger pulse animation
                    if total_size <= 0 and progress_callback:
                        progress_callback(-1)

                    with open(target_path, 'wb') as f:
                        while True:
                            chunk = response.read(1024 * 32)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(int(downloaded / total_size * 100))
                    return True
                return False
        except Exception as e:
            print(f"Update download failed: {e}")
            return False

    @staticmethod
    def run_installer(zip_path):
        """
        Extracts the update and creates a batch script to replace files and restart.
        """
        try:
            temp_dir = os.path.join(os.environ['TEMP'], "VaultPy_Update")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

            # 1. Unzip to temp location
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Most release zips contain a "VaultPy" folder inside
                zip_ref.extractall(temp_dir)

            # Identify the app path and exe path
            # SAFETY CHECK: Only proceed if running as a PyInstaller EXE (Frozen)
            if not getattr(sys, 'frozen', False):
                print("Safety Check: Auto-install skipped because application is running in development mode (Source Code).")
                print(f"Update ZIP is safe at: {zip_path}")
                return False

            app_dir = os.path.dirname(os.path.abspath(sys.executable))
            exe_name = os.path.basename(sys.executable)
            
            # Find the actual content folder in temp
            extracted_app_path = temp_dir
            items = os.listdir(temp_dir)
            # If the zip contains exactly ONE root directory, the app is inside it
            if len(items) == 1 and os.path.isdir(os.path.join(temp_dir, items[0])):
                extracted_app_path = os.path.join(temp_dir, items[0])

            # 3. Create the Batch Script
            bat_path = os.path.join(os.environ['TEMP'], "vaultpy_updater.bat")
            with open(bat_path, "w", encoding="cp1256") as f:
                # timeout /t 2: Wait for main app to close
                # xcopy: Copy all files and subdirectories
                # start: Relaunch
                # %~f0: Delete this batch file
                f.write(f"""@echo off
timeout /t 2 /nobreak > nul
xcopy /s /e /y "{extracted_app_path}\\*" "{app_dir}\\"
start "" "{os.path.join(app_dir, exe_name)}"
del /f /q "{zip_path}"
timeout /t 1 /nobreak > nul
rd /s /q "{temp_dir}"
(goto) 2>nul & del "%~f0"
""")

            # 4. Launch the Batch Script and Exit
            subprocess.Popen(["cmd.exe", "/c", bat_path], shell=True)
            return True
        except Exception as e:
            print(f"Installation setup failed: {e}")
            return False
