"""
news_retriever.py
-----------------
Responsible for fetching and extracting the main content from news article web pages for summarization and scoring.
"""

import logging
from bs4 import BeautifulSoup
import re
try:
    from langdetect import detect
except ImportError:
    detect = None

def extract_article_content(html: str, url: str = None) -> str:
    """
    Extracts the main article text from an HTML document.
    Strategy:
      1. <article> tag if present and >300 chars
      2. Longest <div> or <section> with class/id containing keywords (main, content, body, article, post, entry) and >300 chars
    Cleans whitespace, deduplicates newlines, and fixes broken lists.
    Logs which strategy was used.
    """
    soup = BeautifulSoup(html, 'html.parser')
    # 1. Try <article>
    article_tag = soup.find('article')
    if article_tag and article_tag.get_text(strip=True) and len(article_tag.get_text(strip=True)) > 100:
        text = article_tag.get_text(separator='\n', strip=True)
        cleaned = _clean_article_text(text)
        # language detection: skip non-English content
        if detect:
            try:
                lang = detect(cleaned)
                if lang != 'en':
                    logging.info(f"extract_article_content[{url}]: detected non-English language '{lang}', skipping")
                    return ""
            except Exception as e:
                logging.warning(f"extract_article_content[{url}]: language detection failed: {e}")
        logging.info(f"extract_article_content[{url}]: used <article> tag")
        logging.info(f"extract_article_content[{url}]: first 3000 chars: {cleaned[:3000]}")
        return cleaned
    # 2. Try <div> or <section> with relevant class/id
    candidates = []
    for tag in soup.find_all(['div', 'section']):
        id_class = ' '.join(filter(None, [tag.get('id', ''), ' '.join(tag.get('class', []))])).lower()
        if re.search(r'(main|body|article|content|post|entry)', id_class):
            txt = tag.get_text(separator='\n', strip=True)
            if txt and len(txt) > 300:
                candidates.append(txt)
    if candidates:
        text = max(candidates, key=len)
        cleaned = _clean_article_text(text)
        # language detection: skip non-English content
        if detect:
            try:
                lang = detect(cleaned)
                if lang != 'en':
                    logging.info(f"extract_article_content[{url}]: detected non-English language '{lang}', skipping")
                    return ""
            except Exception as e:
                logging.warning(f"extract_article_content[{url}]: language detection failed: {e}")
        logging.info(f"extract_article_content[{url}]: used content container")
        logging.info(f"extract_article_content[{url}]: first 3000 chars: {cleaned[:3000]}")
        return cleaned
    # 3. Fallback: empty string
    logging.info(f"extract_article_content[{url}]: no suitable container found")
    return ""

def _clean_article_text(text: str) -> str:
    # Remove excess whitespace and deduplicate newlines
    text = re.sub(r'\s+\n', '\n', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    # Fix broken lists: join lines that are part of the same list
    text = re.sub(r'([\n\r])([\-\*•]\s?)', r'\1\2', text)
    return text.strip()