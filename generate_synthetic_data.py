#!/usr/bin/env python3

import json
from pathlib import Path
from typing import List
import logging
from models import GovPage, SyntheticData
import openai
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simplified format
)

# Disable httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class Snippet(BaseModel):
    well_written_snippet: str
    badly_written_snippet: str

class ArticleSnippets(BaseModel):
    snippets: List[Snippet]

# Define our response format
class SynthesisedText(BaseModel):
    poorly_written_article: str

def get_synthetic_text(original_text: str) -> SynthesisedText:
    """Get synthetic text from OpenAI."""
    system_prompt = """
Prompt:

Take the following well-written article and rewrite it in a way that:

Feels rushed and unpolished, like it was written quickly by an amateur.
Uses informal and imprecise language with minor grammatical issues or awkward phrasing.
Occasionally misses details or over-explains simple points, without being completely incoherent.
Avoids extreme confusion but includes mild distractions or offhand comments that feel out of place.
Use the example below to guide your output:

Example:

original_article:
"The solar system consists of the Sun, eight planets, their moons, and a variety of smaller objects like asteroids and comets. The Sun is at the center, providing the gravitational pull that holds the system together. Each planet orbits the Sun at a different distance, creating a wide range of conditions. For example, Mercury is extremely hot due to its proximity to the Sun, while Neptune, much farther away, is cold and covered in ice."

rewritten_article:
"So like, the solar system is made up of the Sun (duh), planets (eight of them now, Pluto got kicked out lol), moons, and a bunch of other stuff like asteroids and comets. The Sun's in the middle, and its gravity keeps everything from flying away or whatever. The planets are all at different distances, which is why some, like Mercury, are roasting hot, and others, like Neptune, are freezing and covered in ice. Pretty wild how that works, right?"

Now rewrite the following article:
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": original_text}
    ]
    
    completion = openai.beta.chat.completions.parse(
        model="gpt-4o-mini",  # Using same model as notebook
        messages=messages,
        response_format=SynthesisedText,
        max_tokens=2048
    )
    
    return completion.choices[0].message.parsed

def process_batch(pages: List[GovPage], start_idx: int, batch_size: int = 10) -> List[GovPage]:
    """Process a batch of pages and add synthetic data."""
    end_idx = min(start_idx + batch_size, len(pages))
    batch = pages[start_idx:end_idx]
    
    for page in batch:
        if page.details.body:
            try:
                logger.info(f"Processing synthetic content for: {page.title}")
                
                # Get poorly written version
                synthetic = get_synthetic_text(page.details.body)
                
                # Get snippets and convert to dict
                snippets = get_article_snippets(page.details.body)
                snippets_dict = snippets.dict()  # Convert to dictionary
                
                # Add both to synthetic data
                page.synthetic_data = SyntheticData(
                    poorly_written_article=synthetic.poorly_written_article,
                    article_snippets=snippets_dict
                )
                
            except Exception as e:
                logger.error(f"Error generating synthetic content for {page.title}: {e}")
    
    return batch

def load_gov_pages(file_path: str) -> List[GovPage]:
    """Load saved JSON data back into GovPage objects."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        logger.info(f"Loading {len(data)} pages from JSON")
        pages = [GovPage(**page_data) for page_data in data]
        
        # Print some stats about loaded data
        doc_types = {}
        for page in pages:
            doc_types[page.document_type] = doc_types.get(page.document_type, 0) + 1
        
        logger.info("Loaded document types:")
        for doc_type, count in doc_types.items():
            logger.info(f"- {doc_type}: {count}")
            
        return pages
        
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise

def get_article_snippets(original_text: str) -> ArticleSnippets:
    """Break article into sections and get summaries for each section."""
    system_prompt = """
Break the following article into logical sections and create poorly written versions that break specific writing principles.
Break the content at natural points such as:
- Heading changes  
- Topic transitions
- Major conceptual shifts
- New procedural steps

For each rewritten section, randomly select and break THREE of these principles:
1. Use excessive jargon and technical language instead of plain English
2. Create long, winding sentences with multiple clauses instead of clear, concise ones 
3. Add irrelevant information and tangents instead of staying focused
4. Mix extremely formal and casual language tones instead of consistency
5. Include unnecessary marketing speak and hyperbole instead of being direct
6. Use passive voice and indirect language instead of active voice
7. Add rhetorical questions instead of clear statements
8. Include redundant words and phrases instead of being concise
9. Use excessive punctuation marks instead of standard punctuation
10. RANDOMLY capitalize WORDS instead of standard capitalization

Format your response to match this example:

snippets:
[
   {
       "well_written_snippet": "The solar system consists of the Sun and the celestial objects bound to it by gravity. These objects include the eight planets and their natural satellites, dwarf planets, asteroids, comets, and countless particles of dust.",
       "badly_written_snippet": "The heliocentric gravitationally-bound astronomical phenomenon that we refer to as our solar system - which btw is like totally mind-blowing when you really think about it - consists primarily (but not exclusively!) of one Class G2V yellow dwarf star, accompanied by various celestial bodies including planetary objects, their respective satellites, and miscellaneous space debris."
   }
]

Now break this article into sections and create poorly written versions of each one by breaking exactly three principles per rewrite:
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": original_text}
    ]
    
    completion = openai.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        response_format=ArticleSnippets
    )
    
    return completion.choices[0].message.parsed

def main():
    start_time = time.time()
    input_file = "./data/gov_pages_with_body_content.json"
    output_file = "./data/gov_pages_with_synthetic_content.json"
    
    # Load the pages
    pages = load_gov_pages(input_file)
    print(f"\n=== Starting Processing ===")
    print(f"Source articles loaded: {len(pages)}")
    
    # Process in batches of 10
    batch_size = 10
    processed_pages = []
    total_snippets = 0
    total_processing_time = 0
    
    for i in range(0, len(pages), batch_size):
        batch_start = time.time()
        batch = process_batch(pages, i, batch_size)
        batch_time = time.time() - batch_start
        total_processing_time += batch_time
        processed_pages.extend(batch)
        
        # Count snippets from this batch
        batch_snippets = 0
        for page in batch:
            if page.synthetic_data and page.synthetic_data.article_snippets:
                batch_snippets = len(page.synthetic_data.article_snippets.snippets)
                total_snippets += batch_snippets
        
        # Print progress
        print(f"\nBatch {i//batch_size + 1} complete:")
        print(f"Articles processed: {len(processed_pages)}")
        print(f"Snippets in this batch: {batch_snippets}")
        print(f"Total snippets created: {total_snippets}")
        print(f"Batch processing time: {batch_time:.1f}s ({batch_time/len(batch):.1f}s per article)")
        
        # Wait 1 second between batches
        if i + batch_size < len(pages):
            print("Waiting for rate limit...")
            time.sleep(1)
    
    # Save processed pages
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([page.dict() for page in processed_pages], f, indent=2, default=str)
    
    total_time = time.time() - start_time
    
    # Final statistics
    print(f"\n=== Processing Complete ===")
    print(f"Source articles: {len(pages)}")
    print(f"Articles rewritten: {len(processed_pages)}")
    print(f"Total snippets created: {total_snippets}")
    print(f"Average snippets per article: {total_snippets/len(processed_pages):.1f}")
    print(f"Total processing time: {total_time:.1f}s")
    print(f"Average time per article: {total_processing_time/len(processed_pages):.1f}s")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main() 