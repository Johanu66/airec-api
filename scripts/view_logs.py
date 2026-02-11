#!/usr/bin/env python3
"""
Log Viewer Utility for AiRec API

Usage:
    python scripts/view_logs.py [options]

Examples:
    python scripts/view_logs.py --tail              # Follow live logs
    python scripts/view_logs.py --errors            # Show only errors
    python scripts/view_logs.py --search "user123"  # Search for specific term
    python scripts/view_logs.py --stats             # Show log statistics
"""

import sys
import os
import re
from collections import Counter
from datetime import datetime
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_log_files():
    """Get all log files in tmp directory"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp')
    if not os.path.exists(log_dir):
        print(f"Log directory not found: {log_dir}")
        return []
    
    log_files = []
    for f in os.listdir(log_dir):
        if f.startswith('app.log'):
            log_files.append(os.path.join(log_dir, f))
    
    return sorted(log_files)


def tail_logs(log_file, lines=100):
    """Display last N lines of log file"""
    try:
        with open(log_file, 'r') as f:
            content = f.readlines()
            for line in content[-lines:]:
                print(line.rstrip())
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
    except Exception as e:
        print(f"Error reading log file: {e}")


def follow_logs(log_file):
    """Follow log file in real-time (like tail -f)"""
    import time
    try:
        with open(log_file, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            print(f"Following {log_file}... (Ctrl+C to stop)")
            print("-" * 80)
            
            while True:
                line = f.readline()
                if line:
                    print(line.rstrip())
                else:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped following logs")
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
    except Exception as e:
        print(f"Error: {e}")


def filter_logs(log_file, level=None, search=None):
    """Filter logs by level or search term"""
    try:
        with open(log_file, 'r') as f:
            for line in f:
                show = True
                
                if level:
                    if level.upper() not in line:
                        show = False
                
                if search:
                    if search.lower() not in line.lower():
                        show = False
                
                if show:
                    print(line.rstrip())
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
    except Exception as e:
        print(f"Error: {e}")


def show_stats(log_files):
    """Show statistics about logs"""
    stats = {
        'total_lines': 0,
        'levels': Counter(),
        'errors': [],
        'warnings': [],
        'dates': Counter()
    }
    
    # Regex pattern for log line
    pattern = r'\[([^\]]+)\] (\w+) in (\w+): (.+)'
    
    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    stats['total_lines'] += 1
                    
                    match = re.match(pattern, line)
                    if match:
                        timestamp, level, module, message = match.groups()
                        stats['levels'][level] += 1
                        
                        # Extract date
                        try:
                            date = timestamp.split()[0]
                            stats['dates'][date] += 1
                        except:
                            pass
                        
                        # Track errors and warnings
                        if level == 'ERROR':
                            stats['errors'].append(message[:100])
                        elif level == 'WARNING':
                            stats['warnings'].append(message[:100])
        except Exception as e:
            print(f"Error reading {log_file}: {e}")
    
    # Print statistics
    print("=" * 80)
    print("LOG STATISTICS")
    print("=" * 80)
    print(f"\nTotal log entries: {stats['total_lines']:,}")
    
    print("\nLog Levels:")
    for level, count in stats['levels'].most_common():
        print(f"  {level:10s}: {count:,}")
    
    print("\nLogs by Date:")
    for date, count in sorted(stats['dates'].items(), reverse=True)[:10]:
        print(f"  {date}: {count:,}")
    
    if stats['errors']:
        print(f"\nRecent Errors ({len(stats['errors'])}):")
        for error in stats['errors'][-5:]:
            print(f"  - {error}")
    
    if stats['warnings']:
        print(f"\nRecent Warnings ({len(stats['warnings'])}):")
        for warning in stats['warnings'][-5:]:
            print(f"  - {warning}")
    
    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(description='AiRec API Log Viewer')
    parser.add_argument('--tail', action='store_true', help='Follow logs in real-time')
    parser.add_argument('--lines', type=int, default=100, help='Number of lines to show')
    parser.add_argument('--errors', action='store_true', help='Show only errors')
    parser.add_argument('--warnings', action='store_true', help='Show only warnings')
    parser.add_argument('--info', action='store_true', help='Show only info')
    parser.add_argument('--debug', action='store_true', help='Show only debug')
    parser.add_argument('--search', type=str, help='Search for specific term')
    parser.add_argument('--stats', action='store_true', help='Show log statistics')
    parser.add_argument('--file', type=str, help='Specific log file to view')
    
    args = parser.parse_args()
    
    # Get log files
    log_files = get_log_files()
    if not log_files:
        print("No log files found in tmp/ directory")
        return
    
    # Use specified file or default to latest
    if args.file:
        log_file = args.file
    else:
        log_file = log_files[0]  # Latest log file
    
    # Show statistics
    if args.stats:
        show_stats(log_files)
        return
    
    # Follow logs
    if args.tail:
        follow_logs(log_file)
        return
    
    # Determine filter level
    level = None
    if args.errors:
        level = 'ERROR'
    elif args.warnings:
        level = 'WARNING'
    elif args.info:
        level = 'INFO'
    elif args.debug:
        level = 'DEBUG'
    
    # Filter or show logs
    if level or args.search:
        filter_logs(log_file, level=level, search=args.search)
    else:
        tail_logs(log_file, lines=args.lines)


if __name__ == '__main__':
    main()
