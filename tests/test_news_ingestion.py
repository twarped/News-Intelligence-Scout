import pytest
import logging
from unittest.mock import patch, Mock


MOCK_NEWSAPI_RESPONSE = {
    "status": "ok",
    "articles": [
        {
            "title": "Title One",
            "source": {"name": "SourceA"},
            "publishedAt": "2025-04-21T10:00:00Z",
            "url": "http://example.com/one",
            "content": "Short summary one."
        },
        {
            "title": "Title Two",
            "source": {"name": "SourceB"},
            "publishedAt": "2025-04-21T12:00:00Z",
            "url": "http://example.com/two",
            "description": "Short summary two."
        }
    ]
}

MOCK_HTML_ARTICLE = """
<html><body><article>The quick brown fox jumps over the lazy dog. The sun was shining brightly in the clear blue sky. The birds were singing their sweet melodies, and the gentle breeze was rustling through the leaves of the trees. It was a beautiful day, full of hope and promise. The world was full of wonder and excitement, and anything seemed possible. The quick brown fox jumps over the lazy dog. The sun was shining brightly in the clear blue sky. The birds were singing their sweet melodies, and the gentle breeze was rustling through the leaves of the trees. It was a beautiful day, full of hope and promise. The world was full of wonder and excitement, and anything seemed possible.</article></body></html>
"""

MOCK_HTML_CONTAINER = """
<html><body><div class='main-content'>The quick brown fox jumps over the lazy dog. The sun was shining brightly in the clear blue sky. The birds were singing their sweet melodies, and the gentle breeze was rustling through the leaves of the trees. It was a beautiful day, full of hope and promise. The world was full of wonder and excitement, and anything seemed possible. The quick brown fox jumps over the lazy dog. The sun was shining brightly in the clear blue sky. The birds were singing their sweet melodies, and the gentle breeze was rustling through the leaves of the trees. It was a beautiful day, full of hope and promise. The world was full of wonder and excitement, and anything seemed possible.</div></body></html>
"""

@patch('src.news_provider.requests.get')
def test_ingest_articles_article_tag(mock_get):
    # Mock NewsAPI response
    mock_resp_api = Mock()
    mock_resp_api.json.return_value = MOCK_NEWSAPI_RESPONSE
    mock_resp_api.raise_for_status = lambda: None
    # Mock HTML fetch for first article
    mock_resp_html = Mock()
    mock_resp_html.text = MOCK_HTML_ARTICLE
    mock_resp_html.raise_for_status = lambda: None
    # Mock HTML fetch for second article
    mock_resp_html2 = Mock()
    mock_resp_html2.text = MOCK_HTML_CONTAINER
    mock_resp_html2.raise_for_status = lambda: None
    # Setup side_effect: first call NewsAPI, then article 1, then article 2
    mock_get.side_effect = [mock_resp_api, mock_resp_html, mock_resp_html2]

    from src.news_provider import NewsAPIProvider
    provider = NewsAPIProvider()
    results = provider.get_articles('Snowflake')
    assert len(results) == 2
    assert results[0]['title'] == 'Title One'
    assert 'quick brown fox' in results[0]['extracted_text']
    assert results[0]['fallback_used'] is None
    assert results[1]['title'] == 'Title Two'
    assert 'quick brown fox' in results[1]['extracted_text']
    assert results[1]['fallback_used'] is None

@patch('src.news_provider.requests.get')
def test_ingest_articles_fallback(mock_get):
    # NewsAPI response
    mock_resp_api = Mock()
    mock_resp_api.json.return_value = MOCK_NEWSAPI_RESPONSE
    mock_resp_api.raise_for_status = lambda: None
    # HTML fetch fails (simulate exception)
    def raise_exc(*a, **kw):
        raise Exception('fail')
    # Setup side_effect: first call NewsAPI, then article 1, then article 2
    mock_get.side_effect = [mock_resp_api, raise_exc, raise_exc]
    from src.news_provider import NewsAPIProvider
    provider = NewsAPIProvider()
    results = provider.get_articles('Snowflake')
    assert len(results) == 2
    assert results[0]['fallback_used'] == 'newsapi_content'
    assert results[1]['fallback_used'] == 'newsapi_content'
    assert 'Short summary' in results[0]['extracted_text']
    assert 'Short summary' in results[1]['extracted_text']
