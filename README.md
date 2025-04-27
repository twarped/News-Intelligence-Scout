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

---

- Environment variables `OPENAI_API_KEY` and `NEWSAPI_KEY` must be set for summarization and news retrieval.
- For more details on configuration, see the code comments in `src/cli.py` and `src/cli_utils.py`.
