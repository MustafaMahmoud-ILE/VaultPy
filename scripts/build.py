import PyInstaller.__main__
import os
import shutil
import sys

# Add parent directory to sys.path so it can find project modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def build_app():
    """Builds the VaultPy application using PyInstaller."""
    print("Starting VaultPy Build Process...")

    # Define paths (Relative to project root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    
    main_script = os.path.join(project_root, "main.py")
    icon_path = os.path.join(project_root, "assets", "icon.png")
    assets_dir = os.path.join(project_root, "assets")

    # PyInstaller arguments
    args = [
        main_script,
        '--name=VaultPy',
        '--onedir',           # One Directory mode
        '--noconsole',        # Hidden console window
        '--windowed',         # GUI application
        '--clean',            # Clean cache
        '--noconfirm',        # Overwrite output directory without asking
        '--exclude-module=PyQt5', # Avoid conflicts with other Qt versions
        f'--icon={icon_path}',
    ]

    # Run PyInstaller
    PyInstaller.__main__.run(args)

    # Post-Build Step: Copy assets directly next to EXE
    output_dir = os.path.join(project_root, 'dist', 'VaultPy')
    dest_assets = os.path.join(output_dir, 'assets')
    if os.path.exists(dest_assets):
        shutil.rmtree(dest_assets)
    shutil.copytree(assets_dir, dest_assets)
    print("Assets successfully bundled next to the executable.")

    print("\nBuild Completed!")
    print(f"Output location: {output_dir}")
    print("Note: The 'dist/VaultPy' folder now contains VaultPy.exe and all required files.")

if __name__ == "__main__":
    build_app()
