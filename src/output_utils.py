"""
output_utils.py
---------------
Handles writing output files (JSON, CSV), ranking articles, and logging setup for News Intelligence Scout.
"""

import os
import re
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json
import csv

def rank_articles(articles):
    """
    Sort articles by score descending and assign rank numbers.
    """
    articles = sorted(articles, key=lambda a: a.get('score', 0), reverse=True)
    for idx, art in enumerate(articles, 1):
        art['rank'] = idx
    return articles

def write_ranked_articles(ranked_articles, json_path, csv_path):
    """
    Write ranked articles to JSON and CSV files with the specified columns.
    Handles logging and error reporting.
    """
    ranked_articles = rank_articles(ranked_articles)
    json_data = []
    for art in ranked_articles:
        json_data.append({
            "Rank": art.get("rank", ""),
            "Score": art.get("score", ""),
            "Publication Date": art.get("published_at", ""),
            "Title": art.get("title", ""),
            "Summary": art.get("summary", ""),
            "Rationale": art.get("rationale", ""),
            "URL": art.get("url", ""),
        })
    try:
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(json_data, jf, ensure_ascii=False, indent=2)
        logging.info(f"Wrote ranked articles to {json_path}")
    except Exception as e:
        logging.error(f"Failed to write JSON results: {e}")
    try:
        with open(csv_path, "w", encoding="utf-8", newline='') as cf:
            writer = csv.writer(cf)
            writer.writerow(["Rank", "Score", "Publication Date", "Title", "Summary", "Rationale", "URL"])
            for art in ranked_articles:
                writer.writerow([
                    str(art.get("rank", "")),
                    str(art.get("score", "")),
                    str(art.get("published_at", "")),
                    str(art.get("title", "")),
                    str(art.get("summary", "")),
                    str(art.get("rationale", "")),
                    str(art.get("url", "")),
                ])
        logging.info(f"Wrote ranked articles to {csv_path}")
    except Exception as e:
        logging.error(f"Failed to write CSV results: {e}")

def safe_filename(base: str) -> str:
    """Return a filesystem-safe version of the input string."""
    return ''.join(e for e in base.lower() if e.isalnum() or e in (' ', '_', '-')).replace(' ', '_')


def get_output_paths(base_name: str, timestamp: str, results_dir: str = "results", brand_name: str = None):
    """
    Return file paths for JSON, CSV, and log files.
    Uses the brand_name if provided, otherwise falls back to a cleaned version of base_name.
    """
    def _clean_name(name):
        import re
        name = name.lower()
        name = re.sub(r'[^a-z0-9]+', '_', name)
        name = re.sub(r'_+', '_', name)
        return name.strip('_')
    if brand_name:
        safe_base = _clean_name(brand_name)
    else:
        safe_base = safe_filename(base_name)
    json_file = os.path.join(results_dir, f"{safe_base}_newsinsight_{timestamp}.json")
    csv_file = os.path.join(results_dir, f"{safe_base}_newsinsight_{timestamp}.csv")
    log_file = os.path.join(results_dir, f"{safe_base}_newsinsight_{timestamp}.logs.txt")
    return json_file, csv_file, log_file


def setup_logging(log_file: str, temp_log_file: str = None):
    """Configure logging to the specified log file. If temp_log_file is given, use it as initial log, then move to log_file."""
    # Remove existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    if temp_log_file:
        handler = RotatingFileHandler(temp_log_file, maxBytes=2*1024*1024, backupCount=2)
    else:
        handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=2)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[handler]
    )

    # If temp_log_file is provided and different from log_file, move it
    if temp_log_file and temp_log_file != log_file:
        import shutil
        shutil.move(temp_log_file, log_file)
        # Reconfigure to final log file
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=2)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(message)s',
            handlers=[handler]
        )
