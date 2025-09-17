"""
Progress tracking utilities for the Video Transcription Pipeline
"""

import sys
import logging
from datetime import datetime


class ProgressTracker:
    """A utility class for tracking and displaying progress"""

    def __init__(self, total_items=0, task_name="Processing"):
        """
        Initialize progress tracker

        Args:
            total_items: Total number of items to process
            task_name: Name of the task being tracked
        """
        self.total_items = total_items
        self.current_item = 0
        self.task_name = task_name
        self.successful = 0
        self.failed = 0
        self.start_time = None
        self.current_item_start = None

    def start(self):
        """Start tracking overall progress"""
        self.start_time = datetime.now()
        print("\n" + "="*70)
        print(f"  {self.task_name.upper()}")
        print(f"  Found {self.total_items} items to process")
        print("="*70)

    def start_item(self, item_name, item_num=None):
        """
        Start tracking a specific item

        Args:
            item_name: Name/description of the current item
            item_num: Item number (if not provided, uses internal counter)
        """
        if item_num is None:
            self.current_item += 1
            item_num = self.current_item
        else:
            self.current_item = item_num

        self.current_item_start = datetime.now()

        # Show overall progress
        if item_num > 1:
            overall_percent = ((item_num - 1) / self.total_items) * 100
            print(f"\n{'='*70}")
            print(f"OVERALL PROGRESS: {overall_percent:.1f}% ({item_num - 1}/{self.total_items} completed)")
            print(f"{'='*70}")

        print(f"\n📹 Processing item {item_num}/{self.total_items}: {item_name}")
        print(f"   Starting at {self.current_item_start.strftime('%H:%M:%S')}")

        # Show initial progress bar
        self.update_progress(0, f"Processing {item_name}...")

    def update_progress(self, percent, message=""):
        """
        Update the progress bar for current item

        Args:
            percent: Percentage complete (0-100)
            message: Optional message to display
        """
        self.print_progress_bar(
            percent, 100,
            prefix=f'   Item {self.current_item}/{self.total_items}:',
            suffix=message,
            length=40
        )

    def complete_item(self, item_name, success=True):
        """
        Mark current item as complete

        Args:
            item_name: Name of the completed item
            success: Whether the item was successful
        """
        if success:
            self.successful += 1
            # Show completion
            self.update_progress(100, f"Completed {item_name}")

            if self.current_item_start:
                duration = (datetime.now() - self.current_item_start).total_seconds()
                print(f"   ✓ Completed in {duration:.1f} seconds")
        else:
            self.failed += 1
            print(f"   ❌ Failed to process {item_name}")

    def finish(self):
        """Display final summary"""
        print("\n" + "="*70)
        print(f"  {self.task_name.upper()} COMPLETE!")
        print(f"  ✓ Successfully processed: {self.successful} items")
        if self.failed > 0:
            print(f"  ❌ Failed: {self.failed} items")
        if self.start_time:
            total_duration = (datetime.now() - self.start_time).total_seconds()
            print(f"  ⏱️  Total time: {total_duration:.1f} seconds")
        print("="*70 + "\n")

    @staticmethod
    def print_progress_bar(current, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
        """
        Print a progress bar to console

        Args:
            current: Current progress value
            total: Total progress value
            prefix: String to display before the bar
            suffix: String to display after the bar
            decimals: Number of decimals in percentage
            length: Character length of the progress bar
            fill: Character to use for filled portion
        """
        if total == 0:
            percent = 100.0
            filled_length = length
        else:
            percent = 100 * (current / float(total))
            filled_length = int(length * current // total)

        bar = fill * filled_length + '░' * (length - filled_length)
        sys.stdout.write(f'\r{prefix} |{bar}| {percent:.{decimals}f}% {suffix}')
        sys.stdout.flush()
        if current >= total:
            print()  # New line when complete


class ProgressLogFormatter(logging.Formatter):
    """Custom log formatter that handles progress messages"""

    def format(self, record):
        if hasattr(record, 'progress'):
            return f"\r{record.getMessage()}"
        return super().format(record)


def setup_logging(logger_name=None):
    """
    Setup logging with progress-aware formatting

    Args:
        logger_name: Name of the logger to configure

    Returns:
        Configured logger instance
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ProgressLogFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    return logger


def format_duration(seconds):
    """
    Format duration in seconds to human-readable format

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2m 15s", "1h 30m")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"