import PyInstaller.__main__
import os
import shutil

def build_app():
    """Builds the VaultPy application using PyInstaller."""
    print("Starting VaultPy Build Process...")

    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "main.py")
    icon_path = os.path.join(script_dir, "assets", "icon.png")
    assets_dir = os.path.join(script_dir, "assets")

    # PyInstaller arguments
    args = [
        main_script,
        '--name=VaultPy',
        '--onedir',           # One Directory mode
        '--noconsole',        # Hidden console window
        '--windowed',         # GUI application
        '--clean',            # Clean cache
        '--exclude-module=PyQt5', # Avoid conflicts with other Qt versions
        f'--icon={icon_path}',
        f'--add-data={assets_dir}{os.pathsep}assets', # Include assets folder
    ]

    # Run PyInstaller
    PyInstaller.__main__.run(args)

    print("\nBuild Completed!")
    print(f"Output location: {os.path.join(script_dir, 'dist', 'VaultPy')}")
    print("Note: The 'dist/VaultPy' folder now contains VaultPy.exe and all required files.")

if __name__ == "__main__":
    build_app()
