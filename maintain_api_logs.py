#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timedelta

LOG_FILE = 'api_usage.json'
ARCHIVE_DIR = 'api_usage_archives'

def update_unknown_endpoints():
    """Update 'unknown' endpoints with better guesses based on timestamps."""
    if not os.path.exists(LOG_FILE):
        print(f"{LOG_FILE} not found. Nothing to update.")
        return
    
    # Load the current data
    try:
        with open(LOG_FILE, 'r') as f:
            usage_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error reading {LOG_FILE}. The file may be corrupted.")
        return
    
    unknown_count = 0
    updated_count = 0
    
    # Process each date's entries
    for date_key, entries in usage_data.items():
        for i, entry in enumerate(entries):
            if isinstance(entry, dict) and entry.get('endpoint') == 'unknown':
                unknown_count += 1
                
                # Try to guess the endpoint based on patterns we know
                timestamp = entry.get('timestamp', '')
                
                # Simple heuristic: check nearby entries with known endpoints
                # Look at entries before and after this one
                nearby_endpoints = []
                for j in range(max(0, i-2), min(len(entries), i+3)):
                    if j != i and isinstance(entries[j], dict) and entries[j].get('endpoint') != 'unknown':
                        nearby_endpoints.append(entries[j].get('endpoint'))
                
                # If we have nearby endpoints, use the most common one
                if nearby_endpoints:
                    # Find most common endpoint
                    endpoint_counts = {}
                    for ep in nearby_endpoints:
                        endpoint_counts[ep] = endpoint_counts.get(ep, 0) + 1
                    most_common = max(endpoint_counts.items(), key=lambda x: x[1])[0]
                    
                    # Update the entry
                    entry['endpoint'] = most_common
                    entry['endpoint_note'] = 'inferred from nearby requests'
                    updated_count += 1
    
    # Save the updated data
    with open(LOG_FILE, 'w') as f:
        json.dump(usage_data, f, indent=2)
    
    print(f"Updated {updated_count} of {unknown_count} unknown endpoints")
    return usage_data

def archive_old_logs(data, days_to_keep=30):
    """Archive logs older than the specified number of days."""
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
    
    today = datetime.now().date()
    cutoff_date = (today - timedelta(days=days_to_keep)).isoformat()
    
    # Separate current and archived data
    current_data = {}
    archive_data = {}
    
    for date_key, entries in data.items():
        if date_key < cutoff_date:
            archive_data[date_key] = entries
        else:
            current_data[date_key] = entries
    
    # If we have data to archive
    if archive_data:
        # Create archive filename with year-month
        year_month = cutoff_date[:7]  # YYYY-MM format
        archive_file = os.path.join(ARCHIVE_DIR, f"api_usage_{year_month}.json")
        
        # If archive file exists, merge with it
        if os.path.exists(archive_file):
            try:
                with open(archive_file, 'r') as f:
                    existing_archive = json.load(f)
                # Merge with new archive data
                for date_key, entries in archive_data.items():
                    if date_key in existing_archive:
                        existing_archive[date_key].extend(entries)
                    else:
                        existing_archive[date_key] = entries
                archive_data = existing_archive
            except json.JSONDecodeError:
                pass  # Use the new archive_data if existing file is corrupted
        
        # Save the archive
        with open(archive_file, 'w') as f:
            json.dump(archive_data, f, indent=2)
        
        # Save the current data back to the main log file
        with open(LOG_FILE, 'w') as f:
            json.dump(current_data, f, indent=2)
        
        print(f"Archived {len(archive_data)} days of logs to {archive_file}")
        print(f"Kept {len(current_data)} days of recent logs in {LOG_FILE}")
    else:
        print(f"No logs older than {days_to_keep} days to archive")

if __name__ == "__main__":
    print("API Usage Log Maintenance Tool")
    print("==============================")
    
    # Parse command line arguments
    days_to_keep = 30  # Default
    if len(sys.argv) > 1:
        try:
            days_to_keep = int(sys.argv[1])
        except ValueError:
            print(f"Invalid days value: {sys.argv[1]}. Using default of 30 days.")
    
    # Update unknown endpoints
    updated_data = update_unknown_endpoints()
    
    # Archive old logs if requested
    if updated_data and days_to_keep > 0:
        archive_old_logs(updated_data, days_to_keep)
    
    print("\nMaintenance complete!")