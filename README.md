# GOV.UK Content Scraper

A tool for extracting and processing content from the GOV.UK Content API (Beta). This tool fetches content, converts HTML to markdown, and saves structured data for further analysis.

## Features

- Fetches content from GOV.UK Content API
- Respects API rate limits (10 requests/second)
- Converts HTML content to markdown
- Handles different document types (guides, answers, etc.)
- Combines multi-part documents into single content
- Saves processed content as structured JSON
- Provides processing statistics
- Generates synthetic data including:
  - Poorly written versions of full articles
  - Paired snippets (well-written and badly-written versions)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/UKGovWebsiteContentScraper.git
cd UKGovWebsiteContentScraper
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Scrape content from GOV.UK:
```bash
python scrape_urls.py
```

2. Generate synthetic data:
```bash
python generate_synthetic_data.py
```

The scraping process will:
- Load URLs from `./data/filtered_gov_uk_paths.csv`
- Process all unique URLs
- Skip navigation and government pages
- Convert HTML content to markdown
- Save results to `./data/gov_pages_with_body_content.json`

The synthetic data generation will:
- Create poorly written versions of full articles
- Break articles into logical snippets
- Create badly written versions of each snippet
- Save all content to `./data/gov_pages_with_synthetic_content.json`

## Data Structure

The output JSON contains an array of documents, each with:
- Title and description
- Document type and schema
- Publication dates
- Markdown-formatted content
- Associated metadata (links, organizations, etc.)
- Synthetic data including:
  - Poorly written version of the full article
  - Collection of snippets (well-written and badly-written pairs)

## Next Steps

The project is moving towards creating a comprehensive dataset for training language models on writing quality. The next phases include:

1. Creating a chain of thought space that maps from badly written versions to well-written versions.

2. Creating a final data mix that contains:
   - Full article rewrites (poorly written versions of complete articles)
   - Snippet rewrites (pairs of well-written and badly-written sections)

The final dataset will primarily consist of snippet pairs, with a smaller number of full article rewrites. Importantly, content used in full article rewrites will not be included in the snippet pairs to avoid data contamination.

This approach will provide:
- Fine-grained examples of writing improvements (snippets)
- Examples of document-level writing improvements (full articles)
- Clear separation between snippet and article data

## API Compliance

This tool follows GOV.UK Content API guidelines:
- Respects rate limits (10 requests/second maximum)
- Processes requests in batches with delays
- Handles 429 (Too Many Requests) responses
- Uses HTTPS for all requests

## Document Types

The tool handles various GOV.UK document types:
- Answers: Single-page content
- Guides: Multi-part documents (automatically combined)
- Skips: government, mainstream_browse_page types

## Error Handling

- Validates API responses
- Reports missing content
- Logs skipped documents
- Provides detailed error messages
- Exits on critical errors

## Support & Issues

- Government departments should raise a ticket with GOV.UK Support
- Other users should contact GOV.UK directly
- Security vulnerabilities should be reported following the [security policy](https://www.gov.uk/help/report-vulnerability)

## License

Content accessed via the GOV.UK Content API is available under the Open Government Licence v3.0, except where otherwise stated.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
