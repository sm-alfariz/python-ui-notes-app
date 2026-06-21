"""Date formatting utilities."""

from datetime import datetime


def format_date(date_str: str) -> str:
    """Format a date string to DD/MM/YYYY HH:MM:SS format.

    Parses the date from database format (YYYY-MM-DD HH:MM:SS) and
    converts it to a more readable format.

    Args:
        date_str: The date string in database format.

    Returns:
        Formatted date string, or the original string if parsing fails.
    """
    if not date_str:
        return ""

    try:
        # Parse the date from database format (YYYY-MM-DD HH:MM:SS)
        dt = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
        # Return formatted date
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        # If parsing fails, return the original string
        return str(date_str)