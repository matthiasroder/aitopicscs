#!/usr/bin/env python3
"""
ArXiv Paper Collector for AI Topics
Queries arXiv API for each keyword from CSO subtopics and stores results in SQLite database.
Handles rate limiting, deduplication, and resume capability.
"""

import sqlite3
import urllib.request
import urllib.parse
import feedparser
import json
import time
import argparse
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import sys
import signal
from pathlib import Path


class ArxivCollector:
    def __init__(self, db_path: str = "arxiv_papers.db", delay: float = 3.0):
        """Initialize the collector with database and API settings."""
        self.db_path = db_path
        self.delay = delay  # Seconds between requests
        self.base_url = "http://export.arxiv.org/api/query"
        self.batch_size = 500  # Results per request
        self.max_results_per_keyword = 2000  # API limit
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('arxiv_collector.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup database
        self.setup_database()
        
        # Graceful shutdown handling
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.shutdown_requested = False
    
    def signal_handler(self, signum, frame):
        """Handle graceful shutdown."""
        self.logger.info("Shutdown signal received. Finishing current operation...")
        self.shutdown_requested = True
    
    def setup_database(self):
        """Create database tables and indexes."""
        self.logger.info(f"Setting up database: {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Papers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    arxiv_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authors TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    categories TEXT NOT NULL,
                    published_date TEXT,
                    updated_date TEXT,
                    pdf_url TEXT,
                    entry_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Keywords tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    total_results INTEGER DEFAULT 0,
                    processed_results INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT
                )
            """)
            
            # Many-to-many relationship
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_keywords (
                    paper_id TEXT NOT NULL,
                    keyword_id INTEGER NOT NULL,
                    PRIMARY KEY (paper_id, keyword_id),
                    FOREIGN KEY (paper_id) REFERENCES papers (arxiv_id),
                    FOREIGN KEY (keyword_id) REFERENCES keywords (id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_categories ON papers (categories)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_published ON papers (published_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_status ON keywords (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_keywords_paper ON paper_keywords (paper_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_keywords_keyword ON paper_keywords (keyword_id)")
            
            conn.commit()
    
    def load_keywords(self, keywords_file: str):
        """Load keywords from file into database."""
        self.logger.info(f"Loading keywords from: {keywords_file}")
        
        with open(keywords_file, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for keyword in keywords:
                cursor.execute("""
                    INSERT OR IGNORE INTO keywords (keyword) VALUES (?)
                """, (keyword,))
            
            conn.commit()
            
        self.logger.info(f"Loaded {len(keywords)} keywords into database")
        return len(keywords)
    
    def build_query_url(self, keyword: str, start: int = 0, max_results: int = None) -> str:
        """Build arXiv API query URL for a keyword."""
        if max_results is None:
            max_results = self.batch_size
            
        # Use comprehensive search across all fields
        search_query = f'all:"{keyword}"'
        
        params = {
            'search_query': search_query,
            'start': start,
            'max_results': min(max_results, self.batch_size),
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"{self.base_url}?{query_string}"
    
    def query_arxiv(self, keyword: str, start: int = 0, max_results: int = None) -> Tuple[List[Dict], int]:
        """Query arXiv API for a specific keyword."""
        url = self.build_query_url(keyword, start, max_results)
        
        try:
            self.logger.debug(f"Querying: {url}")
            response = urllib.request.urlopen(url, timeout=30)
            feed = feedparser.parse(response.read())
            
            # Check for errors in feed
            if hasattr(feed, 'status') and feed.status >= 400:
                raise Exception(f"API returned status {feed.status}")
            
            papers = []
            total_results = int(feed.feed.get('opensearch_totalresults', 0))
            
            for entry in feed.entries:
                # Extract arXiv ID from entry ID
                arxiv_id = entry.id.split('/')[-1]
                if 'v' in arxiv_id:
                    arxiv_id = arxiv_id.split('v')[0]  # Remove version number
                
                # Extract authors
                authors = [author.name for author in getattr(entry, 'authors', [])]
                
                # Extract categories
                categories = []
                if hasattr(entry, 'arxiv_primary_category'):
                    categories.append(entry.arxiv_primary_category.term)
                if hasattr(entry, 'tags'):
                    categories.extend([tag.term for tag in entry.tags if tag.term not in categories])
                
                paper = {
                    'arxiv_id': arxiv_id,
                    'title': entry.title.replace('\n', ' ').strip(),
                    'authors': json.dumps(authors),
                    'abstract': entry.summary.replace('\n', ' ').strip(),
                    'categories': json.dumps(categories),
                    'published_date': getattr(entry, 'published', ''),
                    'updated_date': getattr(entry, 'updated', ''),
                    'pdf_url': next((link.href for link in entry.links if link.type == 'application/pdf'), ''),
                    'entry_url': entry.link
                }
                
                papers.append(paper)
            
            return papers, total_results
            
        except Exception as e:
            self.logger.error(f"Error querying arXiv for '{keyword}': {e}")
            raise
    
    def store_papers(self, papers: List[Dict], keyword_id: int) -> int:
        """Store papers in database with deduplication."""
        stored_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for paper in papers:
                try:
                    # Insert paper (ignore if already exists)
                    cursor.execute("""
                        INSERT OR IGNORE INTO papers 
                        (arxiv_id, title, authors, abstract, categories, 
                         published_date, updated_date, pdf_url, entry_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        paper['arxiv_id'], paper['title'], paper['authors'],
                        paper['abstract'], paper['categories'], paper['published_date'],
                        paper['updated_date'], paper['pdf_url'], paper['entry_url']
                    ))
                    
                    # Link paper to keyword (ignore if already linked)
                    cursor.execute("""
                        INSERT OR IGNORE INTO paper_keywords (paper_id, keyword_id)
                        VALUES (?, ?)
                    """, (paper['arxiv_id'], keyword_id))
                    
                    if cursor.rowcount > 0:
                        stored_count += 1
                        
                except sqlite3.Error as e:
                    self.logger.error(f"Error storing paper {paper['arxiv_id']}: {e}")
            
            conn.commit()
        
        return stored_count
    
    def process_keyword(self, keyword: str, keyword_id: int) -> Dict:
        """Process all papers for a single keyword."""
        self.logger.info(f"Processing keyword: '{keyword}'")
        
        # Update keyword status
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE keywords 
                SET status = 'processing', started_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (keyword_id,))
            conn.commit()
        
        total_processed = 0
        total_stored = 0
        total_results = 0
        start = 0
        
        try:
            while start < self.max_results_per_keyword:
                if self.shutdown_requested:
                    break
                
                # Query API
                papers, api_total_results = self.query_arxiv(
                    keyword, start, min(self.batch_size, self.max_results_per_keyword - start)
                )
                
                if start == 0:
                    total_results = min(api_total_results, self.max_results_per_keyword)
                    self.logger.info(f"Found {api_total_results} total results for '{keyword}' (processing max {total_results})")
                
                # Store papers
                stored_count = self.store_papers(papers, keyword_id)
                total_processed += len(papers)
                total_stored += stored_count
                
                # Update progress
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE keywords 
                        SET total_results = ?, processed_results = ?
                        WHERE id = ?
                    """, (total_results, total_processed, keyword_id))
                    conn.commit()
                
                self.logger.info(f"  Batch {start//self.batch_size + 1}: {len(papers)} papers, {stored_count} new")
                
                # Check if we got fewer results than requested (end of results)
                if len(papers) < self.batch_size:
                    break
                
                start += len(papers)
                
                # Rate limiting
                if start < total_results and not self.shutdown_requested:
                    self.logger.debug(f"Waiting {self.delay} seconds...")
                    time.sleep(self.delay)
            
            # Mark as completed
            status = 'interrupted' if self.shutdown_requested else 'completed'
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE keywords 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, keyword_id))
                conn.commit()
            
            result = {
                'keyword': keyword,
                'total_results': total_results,
                'processed': total_processed,
                'stored': total_stored,
                'status': status
            }
            
            self.logger.info(f"Completed '{keyword}': {total_processed} processed, {total_stored} new papers")
            return result
            
        except Exception as e:
            # Mark as failed
            error_msg = str(e)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE keywords 
                    SET status = 'failed', error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (error_msg, keyword_id))
                conn.commit()
            
            self.logger.error(f"Failed processing '{keyword}': {error_msg}")
            raise
    
    def get_pending_keywords(self) -> List[Tuple[int, str]]:
        """Get list of pending keywords to process."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, keyword FROM keywords 
                WHERE status IN ('pending', 'failed')
                ORDER BY id
            """)
            return cursor.fetchall()
    
    def get_progress_summary(self) -> Dict:
        """Get overall progress summary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Keyword statistics
            cursor.execute("""
                SELECT status, COUNT(*) FROM keywords GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Paper statistics
            cursor.execute("SELECT COUNT(*) FROM papers")
            total_papers = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT paper_id) FROM paper_keywords
            """)
            linked_papers = cursor.fetchone()[0]
            
            # Processing statistics
            cursor.execute("""
                SELECT 
                    SUM(total_results) as total_found,
                    SUM(processed_results) as total_processed
                FROM keywords WHERE status != 'pending'
            """)
            result = cursor.fetchone()
            total_found = result[0] or 0
            total_processed = result[1] or 0
            
            return {
                'keywords': status_counts,
                'papers': {
                    'total_unique': total_papers,
                    'linked': linked_papers
                },
                'processing': {
                    'total_found': total_found,
                    'total_processed': total_processed
                }
            }
    
    def run(self, keywords_file: str, resume: bool = True):
        """Main execution function."""
        self.logger.info("Starting arXiv paper collection")
        
        # Load keywords
        if not resume or not Path(self.db_path).exists():
            self.load_keywords(keywords_file)
        
        # Get pending keywords
        pending_keywords = self.get_pending_keywords()
        self.logger.info(f"Found {len(pending_keywords)} keywords to process")
        
        if not pending_keywords:
            self.logger.info("No pending keywords found")
            return
        
        # Process keywords
        start_time = time.time()
        completed = 0
        
        for keyword_id, keyword in pending_keywords:
            if self.shutdown_requested:
                break
            
            try:
                result = self.process_keyword(keyword, keyword_id)
                completed += 1
                
                # Progress update
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = len(pending_keywords) - completed
                eta = remaining / rate if rate > 0 else float('inf')
                
                self.logger.info(f"Progress: {completed}/{len(pending_keywords)} keywords "
                               f"({completed/len(pending_keywords)*100:.1f}%) "
                               f"ETA: {eta/60:.1f} minutes")
                
                # Show summary every 10 keywords
                if completed % 10 == 0:
                    summary = self.get_progress_summary()
                    self.logger.info(f"Summary: {summary['papers']['total_unique']} unique papers collected")
                
            except Exception as e:
                self.logger.error(f"Failed to process keyword '{keyword}': {e}")
                continue
        
        # Final summary
        summary = self.get_progress_summary()
        self.logger.info("Collection completed!")
        self.logger.info(f"Final summary: {json.dumps(summary, indent=2)}")


def main():
    """Main execution function with command line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect arXiv papers for AI topics from CSO subtopics"
    )
    parser.add_argument(
        "keywords_file",
        help="Path to keywords file (e.g., subtopics_artificial_intelligence_depth_3.txt)"
    )
    parser.add_argument(
        "--database", "-d",
        default="arxiv_papers.db",
        help="SQLite database path (default: arxiv_papers.db)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Delay between API requests in seconds (default: 3.0)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Don't resume from existing database, start fresh"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Show progress summary and exit"
    )
    
    args = parser.parse_args()
    
    collector = ArxivCollector(db_path=args.database, delay=args.delay)
    
    if args.summary_only:
        summary = collector.get_progress_summary()
        print(json.dumps(summary, indent=2))
        return 0
    
    try:
        collector.run(args.keywords_file, resume=not args.no_resume)
        return 0
    except KeyboardInterrupt:
        print("\nCollection interrupted by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())