#!/usr/bin/env python3

import pandas as pd
import sys
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import time
import logging
import html2text
import json
from models import GovPage, GovPageDetails, GovPageLink, GovPageLinks

# Add at top of file after imports
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data(file_path: str) -> pd.DataFrame:
    """Load data from CSV file."""
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

def batch_query_govuk_api(paths: List[str], batch_size: int = 10) -> List[Tuple[str, Optional[dict]]]:
    """
    Query the GOV.UK Content API in batches, respecting rate limits.
    
    Args:
        paths: List of paths to query
        batch_size: Number of requests per batch (max 10 per GOV.UK limits)
    
    Returns:
        List of tuples containing (path, response_data)
    """
    results = []
    
    for i in range(0, len(paths), batch_size):
        batch = paths[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}, paths {i} to {i + len(batch)}")
        
        batch_start = time.time()
        
        for path in batch:
            try:
                response = requests.get(f"https://www.gov.uk/api/content{path}")
                
                if response.status_code == 429:
                    logger.warning("Rate limit hit, waiting before retry...")
                    time.sleep(5)  # Wait 5 seconds before retry
                    response = requests.get(f"https://www.gov.uk/api/content{path}")
                
                response.raise_for_status()
                data = response.json()
                
                # Check for placeholder or redirect content
                if data.get('document_type') in ['placeholder', 'redirect']:
                    logger.info(f"Skipping {path}: {data.get('document_type')} content")
                    results.append((path, None))
                    continue
                
                results.append((path, data))
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error querying API for {path}: {e}")
                results.append((path, None))
        
        # Ensure at least 1 second between batches
        batch_duration = time.time() - batch_start
        if batch_duration < 1:
            time.sleep(1 - batch_duration)
    
    return results

def convert_html_to_markdown(html_content: str) -> str:
    """Convert HTML content to markdown format."""
    h = html2text.HTML2Text()
    h.body_width = 0  # Don't wrap lines
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.ignore_tables = False
    return h.handle(html_content).strip()

def process_pages(df: pd.DataFrame) -> Tuple[List[GovPage], Dict[str, int]]:
    """Process each path and create GovPage objects. Returns (pages, skip_counts)."""
    paths = df['Path'].tolist()
    results = batch_query_govuk_api(paths)
    
    gov_pages = []
    skipped_types = {}
    
    SKIP_TYPES = ['government', 'mainstream_browse_page']
    
    for path, response in results:
        if not response:
            continue
            
        # Skip certain document types
        if response.get('document_type') in SKIP_TYPES:
            doc_type = response.get('document_type')
            logger.info(f"Skipping {doc_type} document: {path}")
            skipped_types[doc_type] = skipped_types.get(doc_type, 0) + 1
            continue
            
        try:
            # Check for important fields before processing
            important_fields = ['title', 'base_path', 'content_id', 'document_type']
            missing_fields = [field for field in important_fields if not response.get(field)]
            if missing_fields:
                logger.warning(f"Missing fields in response for {path}: {missing_fields}")
                logger.warning("Raw response:")
                logger.warning(response)
            
            # For guide-type documents, combine all parts into body
            if response.get('document_type') == 'guide' and 'parts' in response.get('details', {}):
                parts = response['details']['parts']
                combined_body = ""
                for part in parts:
                    if part.get('body'):
                        combined_body += f"\n\n## {part.get('title', 'Untitled Section')}\n\n"
                        combined_body += part['body']
                response['details']['body'] = combined_body
            
            gov_page = GovPage(**response)
            
            # Check if any optional fields were dropped during conversion
            original_keys = set(response.keys())
            model_keys = set(gov_page.dict().keys())
            dropped_fields = original_keys - model_keys
            if dropped_fields:
                logger.warning(f"Fields dropped during model conversion for {path}: {dropped_fields}")
            
            # Convert HTML body to markdown
            if gov_page.details.body:
                gov_page.details.body = convert_html_to_markdown(gov_page.details.body)
            else:
                print("\n=== Found page without body content ===")
                print(f"Path: {path}")
                print(f"Document type: {response.get('document_type')}")
                print("\nFull API Response:")
                print(response)
                sys.exit(1)
                
            gov_pages.append(gov_page)
        except Exception as e:
            logger.error(f"Error processing {path}: {e}")
            print("\nFull API Response that caused error:")
            print(response)
            sys.exit(1)
    
    return gov_pages, skipped_types

def main():
    file_path = "./data/filtered_gov_uk_paths.csv"
    
    print(f"Loading data from: {file_path}")
    df = load_data(file_path)
    
    # Remove duplicates
    df_deduplicated = df.drop_duplicates(subset=['Path'])
    logger.info(f"Processing all {len(df_deduplicated)} unique paths...")
    
    # Process pages and get skip counts
    gov_pages, skipped_types = process_pages(df_deduplicated)
    
    # Count successful document types
    processed_types = {}
    for page in gov_pages:
        processed_types[page.document_type] = processed_types.get(page.document_type, 0) + 1
    
    # Print summary
    print("\n=== Processing Summary ===")
    print(f"Total unique URLs: {len(df_deduplicated)}")
    print(f"Successfully processed: {len(gov_pages)}")
    
    print("\nProcessed documents by type:")
    for doc_type, count in processed_types.items():
        print(f"- {doc_type}: {count}")
    
    print("\nSkipped documents by type:")
    for doc_type, count in skipped_types.items():
        print(f"- {doc_type}: {count}")
    
    # Save to JSON
    output_path = Path("./data/gov_pages_with_body_content.json")
    print(f"\nSaving processed pages to {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([page.dict() for page in gov_pages], f, indent=2, default=str)
    print(f"Saved {len(gov_pages)} pages to {output_path}")

if __name__ == "__main__":
    main() 