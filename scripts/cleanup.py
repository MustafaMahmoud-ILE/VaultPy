import os
import shutil
import glob
import sys

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def cleanup():
    """Performs a deep clean of the project directory."""
    print("Starting Deep Cleanup...")

    # Project root is one level up
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. Folders to delete
    folders_to_delete = [
        os.path.join(project_root, 'build'), 
        os.path.join(project_root, 'dist'), 
        os.path.join(project_root, 'data'), 
        os.path.join(project_root, '.pytest_cache')
    ]

    # Delete folders (including __pycache__ throughout the tree)
    for folder in folders_to_delete:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"  Removed folder: {folder}")
            except Exception as e:
                print(f"  Error removing {folder}: {e}")

    # Delete __pycache__ and binary files based on patterns
    file_patterns = ['*.pyc', '*.pyo', '*.db', '*.spec']
    for root, dirs, files in os.walk(project_root):
        # Remove __pycache__ folders
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                print(f"  Removed folder: {pycache_path}")
            except Exception as e:
                print(f"  Error removing {pycache_path}: {e}")
        
        # Remove binary files matching patterns
        for pattern in file_patterns:
            for file in glob.glob(os.path.join(root, pattern)):
                try:
                    os.remove(file)
                    print(f"  Removed file: {file}")
                except Exception as e:
                    print(f"  Error removing {file}: {e}")

    print("\nCleanup Finished! The project is now safe for GitHub.")

if __name__ == "__main__":
    # Optional: Zip the build result first if you want to keep the EXE
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_path = os.path.join(project_root, 'dist', 'VaultPy')
    if os.path.exists(dist_path):
        print("Build detected. Zipping VaultPy_v1.1.0.zip for distribution...")
        try:
            shutil.make_archive(os.path.join(project_root, 'VaultPy_v1.1.0'), 'zip', dist_path)
            print("  Created: VaultPy_v1.1.0.zip")
        except Exception as e:
            print(f"  Error zipping: {e}")

    cleanup()
