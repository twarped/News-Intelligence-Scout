import pytest
from unittest.mock import patch, Mock

from src.summarizer import summarize_articles

# Test 1: Mock NewsAPI and verify 10 articles are retrieved (English only)
@patch('src.news_provider.requests.get')
def test_newsapi_10_articles(mock_get):
    # Mock NewsAPI response
    mock_api_response = Mock()
    mock_api_response.json.return_value = {
        "articles": [
            {"title": f"Article {i}", "url": f"http://example.com/{i}", "content": "This is an English article about acquisition.", "source": {"name": "TestSource"}, "publishedAt": "2025-04-22T00:00:00Z"}
            for i in range(10)
        ]
    }
    mock_api_response.raise_for_status = lambda: None
    # Mock HTML fetch (always English)
    mock_html_response = Mock()
    mock_html_response.text = "<article>This is an English article about acquisition and growth.</article>"
    mock_html_response.raise_for_status = lambda: None
    mock_get.side_effect = [mock_api_response] + [mock_html_response]*10
    from src.news_provider import NewsAPIProvider
    provider = NewsAPIProvider()
    articles = provider.get_articles('TestCompany')
    assert len(articles) == 10
    assert all('acquisition' in a['extracted_text'] for a in articles)

# Test 2: Mock summarization, verify summaries are deterministic and ≤ 120 words
@patch('src.summarizer.openai')
def test_summarization_deterministic(mock_openai):
    articles = [
        {"extracted_text": "This is a test article about customer experience and compliance. "*10, "title": "Test Title"}
    ]
    # Mock OpenAI client
    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return Mock(choices=[Mock(message=Mock(content="A concise summary about customer experience and compliance."))])
    mock_openai.OpenAI.return_value = FakeClient()
    summarized = list(summarize_articles(articles))
    summary = summarized[0]['summary']
    assert isinstance(summary, str)
    assert len(summary.split()) <= 120
    # Deterministic: repeat should yield same summary
    summarized2 = list(summarize_articles(articles))
    assert summarized2[0]['summary'] == summary
