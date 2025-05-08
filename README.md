# News Intelligence Scout

A command-line tool to retrieve, summarize, and rank recent news articles for a company or search term.

## Usage

Run the CLI with any of the following use cases:

```sh
# Search by company website URL
python main.py "https://snowflake.com"

# Search by a single keyword
python main.py bitcoin

# Search by a multi-word phrase
python main.py "artificial intelligence"

# Specify the number of articles to fetch (long flag)
python main.py bitcoin --num-articles 40

# Specify the number of articles to fetch (short flag)
python main.py "https://acme.com" -n 10
```

- Results are displayed in the terminal as a ranked table.
- Machine-readable results are saved to the `results/` directory as JSON and CSV files.

## Command-line Arguments

You can run News Intelligence Scout with either a company website URL or a search term. Optionally, you can specify how many articles you want to retrieve (default is 25).

```
python main.py <company_url_or_search_term> [--num-articles N]
```

- `<company_url_or_search_term>` (required):
    - The company website URL (e.g. `https://acme.com`) or a search term (e.g. `bitcoin`).
    - The tool will infer the company name from a URL, or use your search term directly.
- `--num-articles N`, `-n N` (optional):
    - The number of news articles to retrieve (default: 25, maximum: 100).
    - Example: `python main.py bitcoin --num-articles 50` will fetch up to 50 articles about "bitcoin".

**Examples:**

- Search by company website:
  ```sh
  python main.py https://snowflake.com
  ```
- Search by keyword/phrase:
  ```sh
  python main.py bitcoin
  ```
- Search by keyword and specify number of articles:
  ```sh
  python main.py "artificial intelligence" --num-articles 40
  ```
- Using the short flag for article count:
  ```sh
  python main.py bitcoin -n 10
  ```

## Help

To see usage instructions:

```
python main.py --help
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/News-Intelligence-Scout.git
   cd News-Intelligence-Scout
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_key_here
   NEWSAPI_KEY=your_newsapi_key_here
   ```

## Output Format

The tool outputs results in both JSON and CSV formats in the `results/` directory. The output structure contains the following fields:

```javascript
{
  "Rank": 1,                         // Position in ranked results (1 = highest score)
  "Score": 85,                       // Opportunity score (0-100)
  "Publication Date": "YYYY-MM-DD",  // Article publication date
  "Title": "Article Title",          // Original headline
  "Summary": "...",                  // AI-generated summary (≤120 words)
  "Rationale": "...",                // Reasoning for the opportunity score
  "URL": "https://..."               // Original article URL
}
```

See the rubric section in `rubric.txt` and `src/summarizer.py` for more details on scoring criteria, etc.

## Project Structure

- `main.py`: Entry point for the CLI application
- `src/`: Core source code
  - `cli.py`: CLI orchestration logic
  - `cli_utils.py`: Utility functions for CLI operations
  - `input_handler.py`: Extracts company names from URLs
  - `news_provider.py`: API interfaces for news retrieval
  - `summarizer.py`: Article summarization and scoring logic
  - `output_utils.py`: File output handling
  - `progress_bar.py`: CLI progress bar implementation
  - `simple_spinner.py`: CLI spinner for activity indication
  - `news_retriever.py`: Content extraction from news articles
  - `llm_utils.py`: LLM client configuration
  - `rubric.txt`: Rubric for scoring articles

---

- Environment variables `OPENAI_API_KEY` and `NEWSAPI_KEY` must be set for summarization and news retrieval.
- For more details on configuration, see the code comments in `src/cli.py` and `src/cli_utils.py`.
