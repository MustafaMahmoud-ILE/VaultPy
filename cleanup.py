import os
import shutil
import glob

def cleanup():
    """Performs a deep clean of the project directory."""
    print("Starting Deep Cleanup...")

    # 1. Folders to delete
    folders_to_delete = [
        'build', 
        'dist', 
        'data', 
        '__pycache__', 
        '.pytest_cache'
    ]

    # 2. File patterns to delete
    file_patterns = [
        '*.spec',
        '*.pyc',
        '*.pyo',
        '*.db'
    ]

    # Delete folders (recursive)
    for folder in folders_to_delete:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"  Removed folder: {folder}")
            except Exception as e:
                print(f"  Error removing {folder}: {e}")

    # Delete files based on patterns (recursive)
    for pattern in file_patterns:
        for file_path in glob.glob(f"**/{pattern}", recursive=True):
            try:
                os.remove(file_path)
                print(f"  Removed file: {file_path}")
            except Exception as e:
                print(f"  Error removing {file_path}: {e}")

    print("\nCleanup Finished! The project is now safe for GitHub.")

if __name__ == "__main__":
    # Optional: Zip the build result first if you want to keep the EXE
    if os.path.exists('dist/VaultPy'):
        print("Build detected. Zipping VaultPy_v1.0.0.zip for distribution...")
        try:
            shutil.make_archive('VaultPy_v1.0.0', 'zip', 'dist/VaultPy')
            print("  Created: VaultPy_v1.0.0.zip")
        except Exception as e:
            print(f"  Error zipping: {e}")

    cleanup()
