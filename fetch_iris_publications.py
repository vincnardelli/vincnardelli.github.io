#!/usr/bin/env python3
"""
Script to fetch publications from IRIS UniCatt and generate Jekyll markdown files.

Usage:
    python fetch_iris_publications.py

The script will:
1. Fetch publications from the IRIS UniCatt researcher page
2. Extract detailed information from each publication page (DOI, ISBN, abstract, etc.)
3. Generate markdown files in the _papers/ directory
4. Skip publications that already exist
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

# IRIS UniCatt researcher page
IRIS_URL = "https://publicatt.unicatt.it/cris/rp/rp74098"
IRIS_BASE = "https://publicatt.unicatt.it"

# Directory for paper markdown files
PAPERS_DIR = Path("_papers")


class IRISListParser(HTMLParser):
    """Parser to extract publication links from IRIS researcher page."""
    def __init__(self):
        super().__init__()
        self.publications = []
        self.current_title = None
        self.current_authors = None
        self.current_year = None
        self.current_handle = None
        self.in_title = False
        self.in_author_line = False
        self.in_link = False
        self.link_stack = []
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Track link tags
        if tag == 'a' and 'href' in attrs_dict:
            href = attrs_dict['href']
            if '/handle/' in href:
                self.current_handle = href
                self.in_link = True
                self.link_stack.append(href)
        
        # Check for title in h5 tag (may be inside a link)
        if tag == 'h5' and attrs_dict.get('class') == 'mb-1 text-secondary':
            self.in_title = True
            self.current_title = ""
        
        # Check for author/year in p tag with mb-1 class
        if tag == 'p' and attrs_dict.get('class') == 'mb-1':
            self.in_author_line = True
            self.current_authors = ""
    
    def handle_endtag(self, tag):
        if tag == 'a' and self.in_link:
            self.in_link = False
            if self.link_stack:
                self.link_stack.pop()
        
        if tag == 'h5' and self.in_title:
            self.in_title = False
        
        if tag == 'p' and self.in_author_line:
            # Parse the author line: "YEAR Author1, Author2; Author3"
            if self.current_authors and self.current_title and self.current_handle:
                parts = self.current_authors.strip().split(' ', 1)
                if len(parts) == 2:
                    year = parts[0]
                    authors_str = parts[1]
                    
                    # Parse authors: format is "Last1, First1; Last2, First2"
                    author_parts = [a.strip() for a in authors_str.split(';')]
                    formatted_authors = []
                    
                    for part in author_parts:
                        items = [i.strip() for i in part.split(',')]
                        i = 0
                        while i < len(items):
                            if i + 1 < len(items):
                                last_name = items[i]
                                first_name = items[i + 1]
                                formatted_authors.append(f"{first_name} {last_name}")
                                i += 2
                            else:
                                formatted_authors.append(items[i])
                                i += 1
                    
                    self.publications.append({
                        'title': self.current_title.strip(),
                        'authors': ', '.join(formatted_authors),
                        'year': year,
                        'handle': self.current_handle
                    })
            
            # Reset for next publication
            self.in_author_line = False
            self.current_authors = None
            self.current_year = None
            # Don't reset title and handle yet - they might be used by next author line
    
    def handle_data(self, data):
        if self.in_title:
            self.current_title += data
        elif self.in_author_line:
            self.current_authors += data


class IRISDetailParser(HTMLParser):
    """Parser to extract detailed information from individual IRIS publication page."""
    def __init__(self):
        super().__init__()
        self.doi = None
        self.isbn = None
        self.abstract = None
        self.journal = None
        self.category = None
        self.url = None
        self.in_abstract = False
        self.in_doi = False
        self.in_journal = False
        self.current_data = ""
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Check for DOI in meta tag
        if tag == 'meta':
            name = attrs_dict.get('name', '')
            if 'citation_doi' in name:
                self.doi = attrs_dict.get('content', '')
            elif 'DCTERMS.bibliographicCitation' in name:
                content = attrs_dict.get('content', '')
                # Extract DOI from citation if present
                doi_match = re.search(r'doi:([^\s\]]+)', content)
                if doi_match and not self.doi:
                    self.doi = doi_match.group(1)
                # Extract journal from citation
                journal_match = re.search(r'&lt;&lt;([^&]+)&gt;&gt;', content)
                if journal_match and not self.journal:
                    self.journal = journal_match.group(1)
        
        # Check for abstract paragraph
        if tag == 'p' and attrs_dict.get('class') == 'searchIndexItemDescription abstractEng':
            self.in_abstract = True
            self.current_data = ""
        
        # Check for DOI link
        if tag == 'a' and 'href' in attrs_dict:
            href = attrs_dict['href']
            if 'dx.doi.org' in href or 'doi.org' in href:
                doi_match = re.search(r'doi[\./]([^\s"\'<>]+)', href)
                if doi_match and not self.doi:
                    self.doi = doi_match.group(1)
            elif href.startswith('http') and not self.url:
                self.url = href
        
        # Check for ISBN (look for ISBN field)
        if tag == 'div' and 'isbn' in attrs_dict.get('class', '').lower():
            self.in_isbn = True
    
    def handle_endtag(self, tag):
        if tag == 'p' and self.in_abstract:
            self.abstract = self.current_data.strip()
            self.in_abstract = False
            self.current_data = ""
    
    def handle_data(self, data):
        if self.in_abstract:
            self.current_data += data


def get_iris_publication_list() -> List[Dict]:
    """Fetch and parse publication list from IRIS researcher page."""
    try:
        req = Request(IRIS_URL, headers={'User-Agent': 'Python IRIS Fetcher'})
        with urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
        
        parser = IRISListParser()
        parser.feed(html)
        return parser.publications
    except Exception as e:
        print(f"Error fetching IRIS publication list: {e}")
        return []


def get_publication_details(handle: str) -> Dict:
    """Fetch detailed information from individual publication page."""
    details = {
        'doi': None,
        'isbn': None,
        'abstract': None,
        'journal': None,
        'url': None
    }
    
    try:
        url = IRIS_BASE + handle if handle.startswith('/') else IRIS_BASE + '/' + handle
        req = Request(url, headers={'User-Agent': 'Python IRIS Fetcher'})
        with urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
        
        parser = IRISDetailParser()
        parser.feed(html)
        
        details['doi'] = parser.doi
        details['isbn'] = parser.isbn
        details['abstract'] = parser.abstract
        details['journal'] = parser.journal
        # Use the handle URL if no other URL found
        if not parser.url:
            details['url'] = url
        else:
            details['url'] = parser.url
        
        # Also try to extract from meta tags more thoroughly
        if not details['doi']:
            doi_match = re.search(r'citation_doi["\']?\s+content=["\']([^"\']+)', html)
            if doi_match:
                details['doi'] = doi_match.group(1)
        
        if not details['abstract']:
            # Try to find abstract in various formats
            abstract_match = re.search(r'<p[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
            if abstract_match:
                abstract_text = abstract_match.group(1)
                # Clean HTML tags
                abstract_text = re.sub(r'<[^>]+>', '', abstract_text)
                details['abstract'] = abstract_text.strip()
        
        if not details['journal']:
            # Try to extract journal from various places
            journal_match = re.search(r'&lt;&lt;([^&]+)&gt;&gt;', html)
            if journal_match:
                details['journal'] = journal_match.group(1)
        
        # Extract ISBN if present
        isbn_match = re.search(r'ISBN[:\s]+([0-9\-X]+)', html, re.IGNORECASE)
        if isbn_match:
            details['isbn'] = isbn_match.group(1)
        
    except Exception as e:
        print(f"Warning: Could not fetch details for {handle}: {e}")
    
    return details


def determine_category(journal: Optional[str], title: Optional[str]) -> str:
    """Determine publication category based on journal and title."""
    # If there's a journal name, it's a Journal Article
    if journal and journal.strip():
        journal_lower = journal.lower()
        title_lower = title.lower() if title else ""
        
        # Exceptions for non-journal publications
        if 'arxiv' in journal_lower or 'preprint' in journal_lower:
            return "Pre-print"
        elif 'conference' in journal_lower or 'proceedings' in journal_lower:
            return "Conference Paper"
        elif 'book' in journal_lower or 'chapter' in title_lower:
            return "Book Chapter"
        else:
            # If there's a journal name, it's a Journal Article
            return "Journal Article"
    
    # No journal, check title for hints
    title_lower = title.lower() if title else ""
    if 'conference' in title_lower or 'proceedings' in title_lower:
        return "Conference Paper"
    elif 'book' in title_lower or 'chapter' in title_lower:
        return "Book Chapter"
    else:
        return "Publication"


def sanitize_filename(name: str, year: Optional[str] = None, month: Optional[str] = None) -> str:
    """Create a safe filename from paper name, year, and month.
    
    Format: YYYY_MM_nome.md
    """
    # Remove special characters, keep only alphanumeric, spaces, and hyphens
    filename = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces and multiple hyphens with single underscore
    filename = re.sub(r'[-\s]+', '_', filename)
    filename = filename.lower()
    
    # Limit length to keep filename reasonable (keep first 6-7 words)
    if len(filename) > 50:
        words = filename.split('_')
        filename = '_'.join(words[:7])
    
    if year:
        month_str = str(month).zfill(2) if month else "01"
        return f"{year}_{month_str}_{filename}.md"
    return f"{filename}.md"


def create_markdown_file(publication: Dict) -> bool:
    """Create a markdown file for a publication."""
    # Use 'name' field if available, otherwise use 'title'
    name = publication.get('name', publication.get('title', ''))
    filename = sanitize_filename(name, publication.get('year'))
    filepath = PAPERS_DIR / filename
    
    if filepath.exists():
        print(f"Skipping {filename} (already exists)")
        return False
    
    # Prepare frontmatter
    # Use 'name' if available, otherwise use 'title'
    pub_name = publication.get('name', publication.get('title', ''))
    year = publication.get('year', 'Unknown')
    month = publication.get('month', '01')
    
    # Create date field for Jekyll (YYYY-MM-DD format)
    # Use first day of the month, or January 1st if month is unknown
    if year != 'Unknown' and year:
        try:
            month_int = int(month) if month else 1
            date_str = f"{year}-{str(month_int).zfill(2)}-01"
        except (ValueError, TypeError):
            date_str = f"{year}-01-01"
    else:
        date_str = None
    
    frontmatter = {
        "name": pub_name,
        "category": publication.get('category', 'Publication'),
        "year": year,
    }
    
    # Add date field if we have a valid year
    if date_str:
        frontmatter["date"] = date_str
    
    if publication.get('authors'):
        frontmatter["authors"] = publication['authors']
    
    if publication.get('journal'):
        frontmatter["journal"] = publication['journal']
    
    # Add link (prefer DOI, otherwise use URL)
    if publication.get('doi'):
        frontmatter["link"] = f"https://doi.org/{publication['doi']}"
    elif publication.get('url'):
        frontmatter["link"] = publication['url']
    
    if publication.get('isbn'):
        frontmatter["isbn"] = publication['isbn']
    
    # Generate markdown content
    content = "---\n"
    for key, value in frontmatter.items():
        if isinstance(value, str) and ('[' in value or '{' in value or ':' in value):
            content += f'{key}: "{value}"\n'
        else:
            content += f"{key}: {value}\n"
    content += "---\n\n"
    
    # Add abstract section
    if publication.get('abstract'):
        content += f"# Abstract\n{publication['abstract']}\n"
    else:
        content += "# Abstract\n*No abstract available.*\n"
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created: {filename}")
        return True
    except Exception as e:
        print(f"Error creating {filename}: {e}")
        return False


def main():
    """Main function to fetch and process publications."""
    PAPERS_DIR.mkdir(exist_ok=True)
    
    print(f"Fetching publications from IRIS UniCatt...")
    publications = get_iris_publication_list()
    
    if not publications:
        print("No publications found.")
        return
    
    print(f"Found {len(publications)} publication(s)")
    print(f"\nFetching detailed information for each publication...")
    
    created_count = 0
    skipped_count = 0
    all_publications = []
    
    for i, pub in enumerate(publications, 1):
        print(f"\n[{i}/{len(publications)}] Processing: {pub['title'][:60]}...")
        
        # Fetch detailed information
        details = get_publication_details(pub['handle'])
        
        # Merge information
        full_pub = {**pub, **details}
        full_pub['category'] = determine_category(details.get('journal'), pub['title'])
        
        # Use 'name' field if available, otherwise use 'title'
        pub_name = full_pub.get('name', full_pub.get('title', ''))
        year = full_pub.get('year', 'Unknown')
        month = full_pub.get('month', '01')
        
        # Create date field for Jekyll (YYYY-MM-DD format)
        if year != 'Unknown' and year:
            try:
                month_int = int(month) if month else 1
                date_str = f"{year}-{str(month_int).zfill(2)}-01"
            except (ValueError, TypeError):
                date_str = f"{year}-01-01"
        else:
            date_str = None
        
        # Prepare JSON entry
        json_entry = {
            "name": pub_name,
            "title": pub_name,
            "category": full_pub.get('category', 'Publication'),
            "year": year,
            "authors": full_pub.get('authors', ''),
            "journal": full_pub.get('journal', ''),
            "abstract": full_pub.get('abstract', ''),
            "doi": full_pub.get('doi', ''),
            "isbn": full_pub.get('isbn', ''),
            "url": full_pub.get('url', ''),
        }
        
        if date_str:
            json_entry["date"] = date_str
        
        # Add link (prefer DOI, otherwise use URL)
        if full_pub.get('doi'):
            json_entry["link"] = f"https://doi.org/{full_pub['doi']}"
        elif full_pub.get('url'):
            json_entry["link"] = full_pub['url']
        
        # Generate filename for individual page
        filename = sanitize_filename(pub_name, year)
        json_entry["filename"] = filename.replace('.md', '')
        json_entry["slug"] = json_entry["filename"]
        
        all_publications.append(json_entry)
        
        # Create markdown file for individual page
        if create_markdown_file(full_pub):
            created_count += 1
        else:
            skipped_count += 1
    
    # Write JSON file
    json_path = Path("_data") / "papers.json"
    json_path.parent.mkdir(exist_ok=True)
    
    # Also write to assets for JavaScript access
    assets_json_path = Path("assets") / "papers.json"
    assets_json_path.parent.mkdir(exist_ok=True)
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_publications, f, indent=2, ensure_ascii=False)
    
    with open(assets_json_path, "w", encoding="utf-8") as f:
        json.dump(all_publications, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Created: {created_count} new publication(s)")
    print(f"  Skipped: {skipped_count} existing publication(s)")
    print(f"  JSON file written to: {json_path} and {assets_json_path}")


if __name__ == "__main__":
    main()

