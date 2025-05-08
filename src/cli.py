"""
cli.py
------
Main entry point and orchestration logic for the News Intelligence Scout CLI.
Handles argument parsing, config validation, article retrieval, summarization, ranking,
output formatting, and robust error/interrupt handling via modular utilities.
"""

import os
import threading
from datetime import datetime
from urllib.parse import urlparse
import logging
from src.input_handler import extract_subject_company_llm
from src.news_provider import NewsAPIProvider
from src.cli_utils import progress_bar, simple_spinner, handle_partial_results
from src.news_retriever import extract_article_content
from src.summarizer import summarize_articles
from src.output_utils import write_ranked_articles
from src.output_utils import get_output_paths, setup_logging
from src.llm_utils import get_llm_client
from src.cli_utils import load_and_validate_config
import requests


def is_valid_url(candidate):
    try:
        result = urlparse(candidate)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def main(query, num_articles):
    """
    Main CLI workflow for News Intelligence Scout.
    Args:
        query (str): Company website URL or search term.
        num_articles (int): Number of articles to retrieve and process.
    Steps:
        1. Validate config and environment.
        2. Extract company name (if URL).
        3. Retrieve news articles.
        4. Summarize and score articles using LLM or fallback.
        5. Rank and pretty-print results, save JSON/CSV/logs.
        6. Handle errors and interruptions robustly, saving partial results.
    """

    print("-" * os.get_terminal_size().columns)
    try:
        # --- Config and setup ---
        config = load_and_validate_config()
        is_url = is_valid_url(query)
        api_key = config['OPENAI_API_KEY']
        # Modular LLM client for summarization
        llm_client = get_llm_client(api_key, model="gpt-4.1-nano", temperature=0, max_tokens=300)
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        # Use the brand name (if inferred) for output filenames
        brand_name_for_files = None
        if is_url:
            # Brand name will be set after extraction below
            brand_name_for_files = None
        else:
            brand_name_for_files = query

        # --- Step 1: Accept input and extract company/search term ---
        if is_url:
            with simple_spinner("Finding Brand Name"):
                subject_company = extract_subject_company_llm(query, llm_client=llm_client)["inferred_name"]
            print(f"\r\033[KFinding Brand Name... done\nBrand Name Found: {subject_company}\n")
            brand_name_for_files = subject_company
        else:
            subject_company = query
            print(f"Treating input as search term: '{subject_company}' (skipping brand name extraction)\n")

        json_file, csv_file, log_file = get_output_paths(query, timestamp, results_dir, brand_name=brand_name_for_files)
        temp_log_file = log_file + ".tmp"
        setup_logging(log_file, temp_log_file)

        with simple_spinner("Waiting for NewsAPI"):
            provider = NewsAPIProvider()
            news_articles = provider.get_articles(subject_company, num_articles=num_articles)
        total_results = len(news_articles)
        print('\r\033[KWaiting for NewsAPI... done')
        skipped_count = 0
        articles = []
        with progress_bar("Processing articles", total=total_results) as progressbar:
            try:
                for idx, a in enumerate(news_articles):
                    url = a.get("url", "")
                    html = ""
                    try:
                        resp = requests.get(url, timeout=6)
                        html = resp.text
                    except Exception as e:
                        logging.warning(f"Failed to fetch article HTML for {url}: {e}")
                    art = a.copy()
                    art["extracted_text"] = extract_article_content(html, url=a.get("url")) if html else a.get("content") or a.get("description") or ""
                    if not art["extracted_text"] or len(art["extracted_text"]) < 100:
                        art["fallback_used"] = 'newsapi_content'
                        art["extracted_text"] = a.get("content") or a.get("description") or ""
                        logging.info(f"extract_article_content: used newsapi_content fallback for '{a.get('title', '')}' ({a.get('url', '')})")
                        if not art["extracted_text"]:
                            logging.info("extract_article_content: newsapi_content fallback is EMPTY.")
                    else:
                        logging.info(f"extract_article_content: printing first 3000 chars: {art['extracted_text'][:3000]}")
                    if not art["extracted_text"]:
                        logging.info(f"SKIPPING ARTICLE due to empty content: '{a.get('title', '')}' ({a.get('url', '')})")
                        skipped_count += 1
                        progressbar.update(count=idx+1, total=total_results, skipped=skipped_count)
                        continue
                    articles.append(art)
                    progressbar.update(count=idx+1, total=total_results, skipped=skipped_count)
            except Exception as e:
                handle_partial_results(ranked=[], articles=articles, json_file=json_file, csv_file=csv_file, log_file=log_file, temp_log_file=temp_log_file)
                raise
        percent = int((total_results / (total_results or 1)) * 100)
        bar = f"[{'#' * (percent // 5):<20}] {percent:3d}% ({total_results}/{total_results}) (skipped: {skipped_count})"
        print(f"\r\033[K{bar}  Processing articles... done")
        total = len(articles)
        if total == 0:
            print("No articles found.")
            return
        # --- Step 3: Summarize and score articles ---
        ranked = []
        with progress_bar("Summarizing articles", total=len(articles)) as progressbar:
            def summarize_progress_callback(idx, total, article, summary, score, rationale):
                progressbar.update(count=idx, total=total)
            try:
                # Summarize each article using LLM or fallback
                for art in summarize_articles(articles, subject_company, progress_callback=summarize_progress_callback):
                    ranked.append(art)
                progressbar.update(count=len(articles), total=len(articles))
            except Exception as e:
                # Save partial results and re-raise on error
                handle_partial_results(ranked=ranked, articles=articles, json_file=json_file, csv_file=csv_file, log_file=log_file, temp_log_file=temp_log_file)
                raise
        percent = int((len(articles) / (len(articles) or 1)) * 100)
        bar = f"[{'#' * (percent // 5):<20}] {percent:3d}% ({len(articles)}/{len(articles)})"
        print(f"\r\033[K{bar}  Summarizing articles... done")

        # --- Step 4: Rank, pretty-print, and save results ---
        from src.output_utils import rank_articles
        ranked = rank_articles(ranked)
        from src.cli_utils import print_article_table
        print_article_table(ranked)
        write_ranked_articles(ranked, json_file, csv_file)
        from src.cli_utils import print_result_paths
        print_result_paths(log_file, json_file, csv_file)

    except KeyboardInterrupt:
        # Save partial results and exit cleanly on Ctrl+C
        from src.cli_utils import handle_keyboard_interrupt
        handle_keyboard_interrupt(locals())

    except Exception as e:
        # Log, save partial results, and exit on unexpected error
        from src.cli_utils import handle_unexpected_exception
        handle_unexpected_exception(e, locals())
