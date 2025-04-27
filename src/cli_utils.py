"""
cli_utils.py
------------
Utility functions and context managers for the News Intelligence Scout CLI.
Encapsulates progress bar/spinner management, CLI output formatting, error handling,
partial result saving, config validation, and other reusable CLI logic.
"""

import threading
from contextlib import contextmanager
import os
import logging
from src.progress_bar import ProgressBar
from src.simple_spinner import SimpleSpinner
from src.output_utils import write_ranked_articles

"""
color_score(score)
-----------------
Colorize a score based on its value.
Returns a click-styled string with green for high scores, yellow for medium scores, and red for low scores.
"""
def color_score(score):
    import click
    if score >= 70:
        return click.style(str(score), fg="green", bold=True)
    elif score >= 30:
        return click.style(str(score), fg="yellow")
    else:
        return click.style(str(score), fg="red")

def print_article_table(ranked, terminal_width=None):
    """
    Pretty-print a list of ranked articles to the terminal in a readable table format.
    Args:
        ranked (list): List of article dicts with ranking and scoring info.
        terminal_width (int, optional): Width of terminal for formatting. Defaults to auto-detect.
    """

    import os
    if terminal_width is None:
        try:
            terminal_width = os.get_terminal_size().columns
        except Exception:
            terminal_width = 120
    for art in ranked:
        print("-" * terminal_width)
        print(f"Rank: {art['rank']}")
        print(f"Score: {color_score(art['score'])}\n")
        print(f"Publication Date: {art['published_at']}\n")
        print(f"Title: {str(art['title'])}\n")
        print(f"Summary: {str(art['summary'])}\n")
        print(f"Rationale: {str(art['rationale'])}\n")
        print(f"URL: {art['url']}")
    print("-" * terminal_width)

def print_result_paths(log_file, json_file, csv_file):
    """
    Print the absolute paths to the log, JSON, and CSV result files after completion.
    Args:
        log_file (str): Path to log file.
        json_file (str): Path to JSON output.
        csv_file (str): Path to CSV output.
    """

    import os
    print(f"Full logs:\n{os.path.abspath(log_file)}")
    print(f"\nJSON Results:\n{os.path.abspath(json_file)}")
    print(f"\nCSV Results:\n{os.path.abspath(csv_file)}")

def load_and_validate_config():
    """
    Load and validate required environment variables for API keys.
    Returns:
        dict: Config dictionary with 'OPENAI_API_KEY' and 'NEWSAPI_KEY'.
    Raises:
        RuntimeError: If any required environment variable is missing.
    """

    import os
    required_keys = ["OPENAI_API_KEY", "NEWSAPI_KEY"]
    config = {k: os.getenv(k) for k in required_keys}
    missing = [k for k, v in config.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return config

def handle_partial_results(ranked=None, articles=None, json_file=None, csv_file=None, log_file=None, temp_log_file=None):
    """
    Save partial results and print file/log locations after interruption or error.
    Args:
        ranked (list, optional): Ranked articles to save.
        articles (list, optional): Unranked articles to save if ranking failed.
        json_file (str): Path to JSON output.
        csv_file (str): Path to CSV output.
        log_file (str): Path to main log file.
        temp_log_file (str): Path to temp log file (if main log not available).
    """

    """
    Save partial results and print file/log locations after interruption or error.
    """
    if ranked:
        ranked.sort(key=lambda a: a.get('score', 0), reverse=True)
        for idx, art in enumerate(ranked, 1):
            art['rank'] = idx
        write_ranked_articles(ranked, json_file, csv_file)
    elif articles:
        write_ranked_articles(articles, json_file, csv_file)
    print(f"\n{'-' * os.get_terminal_size().columns}")
    print("\nAborting!\n")
    print("\n[INFO] Partial results saved to:")
    if log_file:
        print(f"\nFull logs:\n{os.path.abspath(log_file)}")
    elif temp_log_file:
        print(f"\nFull logs:\n{os.path.abspath(temp_log_file)}")
    if json_file:
        print(f"\nJSON Results:\n{os.path.abspath(json_file)}")
    if csv_file:
        print(f"\nCSV Results:\n{os.path.abspath(csv_file)}")

def handle_keyboard_interrupt(local_vars):
    """
    Handle KeyboardInterrupt (Ctrl+C) in the CLI: save partial results and exit cleanly.
    Args:
        local_vars (dict): Locals from the calling scope for context.
    """

    handle_partial_results(
        ranked=local_vars.get('ranked'),
        articles=local_vars.get('articles'),
        json_file=local_vars.get('json_file'),
        csv_file=local_vars.get('csv_file'),
        log_file=local_vars.get('log_file'),
        temp_log_file=local_vars.get('temp_log_file'),
    )
    import sys
    sys.exit(1)

def handle_unexpected_exception(e, local_vars):
    """
    Handle unexpected exceptions in the CLI: log the error, save partial results, and exit.
    Args:
        e (Exception): The exception that was raised.
        local_vars (dict): Locals from the calling scope for context.
    """

    print(f"Unexpected error: {e}")
    import logging
    logging.exception(f"Unexpected error: {e}")
    handle_partial_results(
        ranked=local_vars.get('ranked'),
        articles=local_vars.get('articles'),
        json_file=local_vars.get('json_file'),
        csv_file=local_vars.get('csv_file'),
        log_file=local_vars.get('log_file'),
        temp_log_file=local_vars.get('temp_log_file'),
    )
    import sys
    sys.exit(1)


@contextmanager
def progress_bar(message, total=None, skipped=0):
    pb = ProgressBar(message, total=total, skipped=skipped)
    thread = threading.Thread(target=pb.run)
    thread.start()
    try:
        yield pb
    finally:
        pb.stop()
        thread.join()

@contextmanager
def simple_spinner(message):
    sp = SimpleSpinner(message)
    thread = threading.Thread(target=sp.run)
    thread.start()
    try:
        yield sp
    finally:
        sp.stop()
        thread.join()
