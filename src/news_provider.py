"""
news_provider.py
----------------
Defines the NewsProvider interface and concrete provider implementations for retrieving news articles from APIs (e.g., NewsAPI.org).
Abstracts API logic for easy swapping and extension.
"""

from typing import List, Dict
import logging
import os
import requests
from datetime import datetime, timedelta, UTC
from bs4 import BeautifulSoup

class NewsProvider:
    """
    Abstract news provider interface. Implement get_articles to retrieve news articles for a company.
    """
    def get_articles(self, subject_company: str, num_articles: int = 25) -> List[Dict]:
        """
        Retrieve news articles for the given company/brand using an API.
        Args:
            subject_company (str): The company or brand to search for.
            num_articles (int): Number of articles to retrieve (default 25).
        Returns:
            List[Dict]: Each dict must have these keys:
                {
                    "title": str,
                    "source": str,
                    "published_at": str,
                    "url": str,
                    "extracted_text": str,
                    "fallback_used": str or None
                }
        """
        raise NotImplementedError

class NewsAPIProvider(NewsProvider):
    """
    News provider implementation using NewsAPI.org.
    """
    def get_articles(self, subject_company: str, num_articles: int = 25) -> List[Dict]:
        """
        Retrieve news articles for the given company/brand using NewsAPI.org.
        Args:
            subject_company (str): The company or brand to search for.
            num_articles (int): Number of articles to retrieve (default 25).
        Returns:
            List[Dict]: List of article dicts.
        """
        from src.news_retriever import extract_article_content
        NEWS_API_KEY = os.getenv("NEWSAPI_KEY")
        if not NEWS_API_KEY:
            raise RuntimeError("NewsAPI key not found in environment.")
        today = datetime.now(UTC).date()
        from_date = today - timedelta(days=30)
        params = {
            "q": subject_company,
            "from": from_date.isoformat(),
            "to": today.isoformat(),
            "language": "en",
            "sortBy": "publishedAt",
            "apiKey": NEWS_API_KEY,
            "pageSize": num_articles,
        }
        api_url = "https://newsapi.org/v2/everything"
        resp = requests.get(api_url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for a in data.get("articles", []):
            url = a.get("url", "")
            fallback_used = None
            extracted_text = ""
            if url:
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
                    }
                    html_resp = requests.get(url, timeout=12, headers=headers)
                    html_resp.raise_for_status()
                    extracted_text = extract_article_content(html_resp.text)
                    if not extracted_text or len(extracted_text) < 300:
                        raise ValueError('extracted_text too short')
                except Exception as e:
                    logging.info(f"NewsAPIProvider: fallback to NewsAPI content for {url} ({e})")
                    fallback_used = 'newsapi_content'
                    extracted_text = a.get("content") or a.get("description") or ""
            else:
                fallback_used = 'newsapi_content'
                extracted_text = a.get("content") or a.get("description") or ""
            articles.append({
                "title": a.get("title", ""),
                "source": (a.get("source") or {}).get("name", ""),
                "published_at": a.get("publishedAt", ""),
                "url": url,
                "extracted_text": extracted_text,
                "fallback_used": fallback_used
            })
        return articles
