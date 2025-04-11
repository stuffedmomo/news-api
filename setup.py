#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import argparse

def ensure_directory(directory):
    """Ensure a directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        os.makedirs(directory)
    return directory

def install_dependencies():
    """Install required Python packages."""
    required_packages = [
        "requests",
        "python-dotenv",
        "feedparser",
        "beautifulsoup4",
        "markdown",
        "flask"
    ]
    
    print("Installing required Python packages...")
    for package in required_packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError:
            print(f"Failed to install {package}. Please install it manually.")
            return False
    
    print("All dependencies installed successfully!")
    return True

def setup_directories():
    """Set up the project directories."""
    # Project root is where this script is located
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create required directories
    directories = {
        "project_root": project_root,
        "news_data": ensure_directory(os.path.join(project_root, "news_data")),
        "web": ensure_directory(os.path.join(project_root, "web")),
        "web_css": ensure_directory(os.path.join(project_root, "web", "css")),
        "web_js": ensure_directory(os.path.join(project_root, "web", "js")),
        "cache": ensure_directory(os.path.join(project_root, "cache")),
        "feedback_data": ensure_directory(os.path.join(project_root, "feedback_data"))
    }
    
    return directories

def create_env_file(directories, api_key=None):
    """Create a .env file with the NEWS_API_KEY."""
    if api_key is None:
        api_key = input("Enter your NewsAPI key (or leave blank to skip): ").strip()
    
    env_path = os.path.join(directories["project_root"], ".env")
    
    # Don't overwrite existing .env file unless explicitly told to
    if os.path.exists(env_path):
        overwrite = input(".env file already exists. Overwrite? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Skipping .env file creation")
            return
    
    with open(env_path, 'w') as f:
        f.write(f"NEWS_API_KEY={api_key}\n")
    
    print(f".env file created at {env_path}")

def create_feedback_files(directories):
    """Create initial feedback data files."""
    feedback_dir = directories["feedback_data"]
    
    feedback_files = {
        "article_feedback.json": {"articles": {}},
        "source_ratings.json": {"sources": {}},
        "keyword_ratings.json": {"keywords": {}}
    }
    
    for filename, initial_data in feedback_files.items():
        file_path = os.path.join(feedback_dir, filename)
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write(str(initial_data).replace("'", "\""))
            print(f"Created {filename}")

def main():
    parser = argparse.ArgumentParser(description="Set up the UPSC News Portal project")
    parser.add_argument('--api-key', help="Your NewsAPI key")
    parser.add_argument('--full-setup', action='store_true', help="Perform a full setup including dependencies")
    
    args = parser.parse_args()
    
    print("===== UPSC News Portal Setup =====")
    
    # Install dependencies
    if args.full_setup and not install_dependencies():
        print("Failed to install dependencies. Setup aborted.")
        return
    
    # Set up directories
    directories = setup_directories()
    
    # Create .env file
    create_env_file(directories, args.api_key)
    
    # Create feedback files
    create_feedback_files(directories)
    
    print("\nSetup completed successfully!")
    print("\nTo start the web server:")
    print("  python upsc_web_server.py")
    print("\nTo fetch daily news:")
    print("  python upsc_news_daily.py")

if __name__ == "__main__":
    main() 