import os
import json
import csv
from src.output_utils import write_ranked_articles

def test_output_generation(tmp_path):
    articles = [
        {
            "rank": 1,
            "score": 85,
            "published_at": "2025-04-22",
            "title": "Company X Announces New Product Line",
            "summary": "Company X has unveiled its new product line, focusing on sustainability...",
            "rationale": "The product launch aligns with Red Pepper’s interest in CX initiatives.",
            "url": "https://example.com/news/article-1"
        },
        {
            "rank": 2,
            "score": 70,
            "published_at": "2025-04-20",
            "title": "Company X Expands into Europe",
            "summary": "Company X is expanding its operations into the European market...",
            "rationale": "Expansion into a new region signals business growth.",
            "url": "https://example.com/news/article-2"
        },
    ]
    json_path = tmp_path / "output.json"
    csv_path = tmp_path / "output.csv"
    write_ranked_articles(articles, str(json_path), str(csv_path))
    # Check JSON
    with open(json_path, encoding="utf-8") as jf:
        data = json.load(jf)
        assert isinstance(data, list)
        assert data[0]["Rank"] == 1
        assert data[0]["Title"].startswith("Company X")
    # Check CSV
    with open(csv_path, encoding="utf-8") as cf:
        reader = csv.reader(cf)
        rows = list(reader)
        assert rows[0] == ["Rank", "Score", "Publication Date", "Title", "Summary", "Rationale", "URL"]
        assert rows[1][0] == "1"
        assert "Company X" in rows[1][3]
