import os
import logging
import pytest
from src.news_retriever import extract_article_content

# Configure logging to print to console for test feedback
def setup_module(module):
    logging.basicConfig(level=logging.INFO)

def load_html(filename):
    with open(os.path.join(os.path.dirname(__file__), 'html_samples', filename), encoding='utf-8') as f:
        return f.read()

def test_article_tag_extraction():
    html = load_html('article_tag.html')
    text = extract_article_content(html)
    assert 'This is the main article body' in text
    assert len(text) > 300

def test_content_container_extraction():
    html = load_html('content_container.html')
    text = extract_article_content(html)
    assert 'Main content goes here' in text
    assert len(text) > 300

def test_no_container_found():
    html = load_html('no_article.html')
    text = extract_article_content(html)
    assert text == ''

# You would place sample HTML files in tests/html_samples/ for these tests to run.
# article_tag.html should have a large <article> tag
# content_container.html should have a large <div> or <section> with class/id like 'main-content'
# no_article.html should have no suitable containers
