import click
from src.cli import main as cli_main

@click.command(help="Retrieve, summarize, and rank recent news articles for a company or search term.")
@click.argument(
    'query',
    metavar='<company_url_or_search_term>',
    nargs=1,
    required=True,
    type=str,
    help="Company website URL (e.g. 'https://acme.com') or a search term (e.g. 'bitcoin'). "
         "If a URL is provided, the tool will extract the company name; otherwise, it uses your search term directly."
)
@click.option(
    '--num-articles', '-n',
    default=25,
    show_default=True,
    metavar='N',
    help="Number of news articles to retrieve (default: 25, max: 100)."
)
def main(query, num_articles):
    """Retrieve, summarize, and rank recent news articles for a company or search term."""
    cli_main(query, num_articles)

if __name__ == "__main__":
    main()