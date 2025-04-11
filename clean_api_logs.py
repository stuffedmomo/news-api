#!/usr/bin/env python3
import json
import os

LOG_FILE = 'api_usage.json'

def clean_api_logs():
    """Clean up the API usage logs by removing incorrect dates and standardizing formats."""
    if not os.path.exists(LOG_FILE):
        print(f"{LOG_FILE} not found. Nothing to clean.")
        return
    
    # Load the current data
    try:
        with open(LOG_FILE, 'r') as f:
            usage_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error reading {LOG_FILE}. The file may be corrupted.")
        return
    
    # Clean up the data
    clean_data = {}
    for date_key, entries in usage_data.items():
        # Skip any entries with incorrect dates (e.g., 2025-04-10 entries with 2025-04-11 timestamps)
        if date_key == '2025-04-10' and any('2025-04-11' in str(entry) for entry in entries):
            print(f"Skipping {date_key} entries with incorrect timestamps")
            continue
            
        # Standardize all entries to the new format
        clean_entries = []
        for entry in entries:
            if isinstance(entry, str):
                # Convert string timestamps to objects
                clean_entries.append({"timestamp": entry, "endpoint": "unknown"})
            elif isinstance(entry, dict):
                # Keep dictionaries as is
                clean_entries.append(entry)
        
        if clean_entries:
            clean_data[date_key] = clean_entries
    
    # Save the cleaned data
    with open(LOG_FILE, 'w') as f:
        json.dump(clean_data, f, indent=2)
    
    print(f"Cleaned {LOG_FILE}. Removed incorrect dates and standardized {len(clean_data)} days of entries.")

if __name__ == "__main__":
    clean_api_logs()