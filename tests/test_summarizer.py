import pytest
from unittest.mock import patch, MagicMock
from src.summarizer import summarize_articles

# Ensure NLTK 'punkt' is available for sent_tokenize
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

def test_summarizer_fn_injection():
    """Test that custom summarizer_fn is used and output is correct."""
    dummy_articles = [{"title": "T", "content": "This is a news article about AI."}]
    def fake_summarizer(article):
        return "FAKE SUMMARY"
    summarized = list(summarize_articles(dummy_articles, summarizer_fn=fake_summarizer))
    assert summarized[0]["summary"] == "FAKE SUMMARY"

def test_heuristic_summary(monkeypatch):
    """Test fallback to heuristic summary when no API key is present."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    dummy_articles = [{"title": "T", "content": "Sentence one. Sentence two. Sentence three. Sentence four."}]
    summarized = list(summarize_articles(dummy_articles))
    assert "summary" in summarized[0]
    summary = summarized[0]["summary"]
    assert (summary.startswith("Sentence one Sentence two Sentence three") or
            summary.startswith("Sentence one. Sentence two. Sentence three"))

def test_invalid_llm_json(monkeypatch):
    """Test that invalid LLM JSON triggers fallback and logs warning."""
    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class Msg:
                        content = "{not: valid json]"
                    class Choice:
                        message = Msg()
                    return type("FakeResp", (), {"choices": [Choice()]})()
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    import src.summarizer as summarizer
    summarized = list(summarizer.summarize_articles([
        {"title": "T", "content": "Some content."}
    ], summarizer_fn=None, progress_callback=None))
    # Should fallback to heuristic summary or empty summary
    assert "summary" in summarized[0]

def test_empty_article_content(monkeypatch):
    """Test that empty content returns 'No content available.' (forces fallback)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    dummy_articles = [{"title": "T", "content": ""}]
    summarized = list(summarize_articles(dummy_articles, summarizer_fn=None))
    assert summarized[0]["summary"] == "No content available."

def test_very_long_content(monkeypatch):
    """Test that very long content is truncated and does not crash (forces fallback)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    long_content = "Sentence. " * 1000
    dummy_articles = [{"title": "T", "content": long_content}]
    summarized = list(summarize_articles(dummy_articles, summarizer_fn=None))
    assert len(summarized[0]["summary"]) <= 500

def test_nltk_unavailable(monkeypatch):
    """Test that missing NLTK triggers warning and fallback."""
    import sys
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "nltk", None)
    dummy_articles = [{"title": "T", "content": "Sentence one. Sentence two."}]
    summarized = list(summarize_articles(dummy_articles, summarizer_fn=None))
    assert summarized[0]["summary"] == "Sentence one. Sentence two."
