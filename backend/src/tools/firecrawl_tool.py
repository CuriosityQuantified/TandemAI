"""
Firecrawl Web Research Tool for ATLAS Research Agents
Provides web search and content extraction capabilities using Firecrawl API
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from functools import lru_cache
import asyncio

try:
    from firecrawl import FirecrawlApp
except ImportError:
    FirecrawlApp = None

from ..agui.tool_events import broadcast_tool_call

logger = logging.getLogger(__name__)

# In-memory cache for search results (with TTL)
_search_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = timedelta(hours=1)  # Cache for 1 hour


class FirecrawlTool:
    """Wrapper for Firecrawl API with caching and error handling."""

    def __init__(self):
        """Initialize Firecrawl client with API key from environment."""
        api_key = os.getenv('FIRECRAWL_API_KEY')

        if not api_key:
            logger.warning("FIRECRAWL_API_KEY not found in environment")
            self.client = None
        elif FirecrawlApp:
            try:
                self.client = FirecrawlApp(api_key=api_key)
                logger.info("Firecrawl client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Firecrawl client: {e}")
                self.client = None
        else:
            logger.error("firecrawl-py package not installed")
            self.client = None

    def _get_cache_key(self, query: str, operation: str) -> str:
        """Generate a cache key for the query."""
        return hashlib.md5(f"{operation}:{query}".encode()).hexdigest()

    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached data is still valid based on TTL."""
        if 'cached_at' not in cached_data:
            return False

        cached_time = datetime.fromisoformat(cached_data['cached_at'])
        return datetime.now() - cached_time < _cache_ttl

    @broadcast_tool_call("firecrawl_web_search", capture_result=True, capture_params=True)
    def web_search(self,
                   query: str,
                   max_results: int = 5,
                   use_cache: bool = True,
                   task_id: str = "default") -> Dict[str, Any]:
        """
        Search the web using Firecrawl API.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            use_cache: Whether to use cached results if available
            task_id: Task identifier for event broadcasting

        Returns:
            Dictionary with search results including titles, URLs, and snippets
        """
        if not self.client:
            return {
                "status": "error",
                "error": "Firecrawl client not initialized",
                "query": query
            }

        # Check cache first
        cache_key = self._get_cache_key(query, "search")
        if use_cache and cache_key in _search_cache:
            cached = _search_cache[cache_key]
            if self._is_cache_valid(cached):
                logger.info(f"Returning cached results for query: {query}")
                return cached['data']

        try:
            # Perform the search
            logger.info(f"Searching web for: {query}")
            search_params = {
                'query': query,
                'limit': max_results,
                'format': 'markdown'  # Get results in markdown format
            }

            results = self.client.search(query, search_params)

            # Structure the response
            formatted_results = {
                "status": "success",
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results": []
            }

            # Process each result
            for idx, result in enumerate(results.get('data', [])[:max_results]):
                formatted_results["results"].append({
                    "title": result.get('title', 'No title'),
                    "url": result.get('url', ''),
                    "snippet": result.get('snippet', result.get('description', '')),
                    "content": result.get('markdown', result.get('content', '')),
                    "metadata": result.get('metadata', {})
                })

            # Cache the results
            if use_cache:
                _search_cache[cache_key] = {
                    'cached_at': datetime.now().isoformat(),
                    'data': formatted_results
                }

            logger.info(f"Found {len(formatted_results['results'])} results for: {query}")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching web: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }

    @broadcast_tool_call("firecrawl_scrape", capture_result=True, capture_params=True)
    def scrape_content(self,
                       url: str,
                       include_markdown: bool = True,
                       use_cache: bool = True,
                       task_id: str = "default") -> Dict[str, Any]:
        """
        Scrape content from a specific URL.

        Args:
            url: URL to scrape
            include_markdown: Whether to include markdown version
            use_cache: Whether to use cached content if available
            task_id: Task identifier for event broadcasting

        Returns:
            Dictionary with scraped content including title, text, and metadata
        """
        if not self.client:
            return {
                "status": "error",
                "error": "Firecrawl client not initialized",
                "url": url
            }

        # Check cache
        cache_key = self._get_cache_key(url, "scrape")
        if use_cache and cache_key in _search_cache:
            cached = _search_cache[cache_key]
            if self._is_cache_valid(cached):
                logger.info(f"Returning cached content for URL: {url}")
                return cached['data']

        try:
            logger.info(f"Scraping content from: {url}")

            # Scrape the URL
            scrape_params = {
                'formats': ['markdown'] if include_markdown else [],
                'onlyMainContent': True,  # Focus on main content
                'includeHtml': False  # Don't include raw HTML
            }

            result = self.client.scrape_url(url, scrape_params)

            # Structure the response
            formatted_result = {
                "status": "success",
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "title": result.get('metadata', {}).get('title', 'No title'),
                "content": result.get('content', ''),
                "markdown": result.get('markdown', '') if include_markdown else None,
                "metadata": {
                    "description": result.get('metadata', {}).get('description', ''),
                    "keywords": result.get('metadata', {}).get('keywords', ''),
                    "author": result.get('metadata', {}).get('author', ''),
                    "published_date": result.get('metadata', {}).get('publishedDate', ''),
                    "language": result.get('metadata', {}).get('language', 'en')
                }
            }

            # Cache the result
            if use_cache:
                _search_cache[cache_key] = {
                    'cached_at': datetime.now().isoformat(),
                    'data': formatted_result
                }

            logger.info(f"Successfully scraped content from: {url}")
            return formatted_result

        except Exception as e:
            logger.error(f"Error scraping URL {url}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "url": url,
                "timestamp": datetime.now().isoformat()
            }

    def batch_scrape(self,
                     urls: List[str],
                     max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs with rate limiting.

        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent requests

        Returns:
            List of scraped content dictionaries
        """
        results = []

        # Process in batches to respect rate limits
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i:i + max_concurrent]
            batch_results = []

            for url in batch:
                result = self.scrape_content(url)
                batch_results.append(result)

                # Small delay between requests
                if len(batch) > 1:
                    import time
                    time.sleep(0.5)

            results.extend(batch_results)

        return results

    def search_and_summarize(self,
                            query: str,
                            max_results: int = 3,
                            summarize_type: str = "key_points") -> Dict[str, Any]:
        """
        Search and provide a summary of the results.

        Args:
            query: Search query
            max_results: Number of results to summarize
            summarize_type: Type of summary (key_points, brief, detailed)

        Returns:
            Search results with summaries
        """
        # First, perform the search
        search_results = self.web_search(query, max_results)

        if search_results.get('status') != 'success':
            return search_results

        # For each result, scrape more detailed content if needed
        enhanced_results = search_results.copy()
        enhanced_results['summaries'] = []

        for result in search_results.get('results', []):
            url = result.get('url')
            if url:
                # Get full content
                scraped = self.scrape_content(url)

                if scraped.get('status') == 'success':
                    # Create summary based on type
                    content = scraped.get('markdown', scraped.get('content', ''))

                    if summarize_type == "key_points":
                        summary = self._extract_key_points(content)
                    elif summarize_type == "brief":
                        summary = content[:500] + "..." if len(content) > 500 else content
                    else:  # detailed
                        summary = content[:1500] + "..." if len(content) > 1500 else content

                    enhanced_results['summaries'].append({
                        'url': url,
                        'title': result.get('title'),
                        'summary': summary,
                        'summary_type': summarize_type
                    })

        return enhanced_results

    def _extract_key_points(self, content: str) -> str:
        """Extract key points from content (simple implementation)."""
        # This is a simple implementation
        # In production, you might want to use an LLM for better summarization
        lines = content.split('\n')
        key_points = []

        for line in lines[:10]:  # Look at first 10 lines
            line = line.strip()
            if line and (line.startswith('•') or
                        line.startswith('-') or
                        line.startswith('*') or
                        line[0].isdigit()):
                key_points.append(line)

        if not key_points:
            # Fall back to first few sentences
            sentences = content.split('.')[:3]
            key_points = [s.strip() + '.' for s in sentences if s.strip()]

        return '\n'.join(key_points[:5])  # Return top 5 points

    def clear_cache(self):
        """Clear the search cache."""
        global _search_cache
        _search_cache = {}
        logger.info("Firecrawl cache cleared")


# Module-level functions for direct tool registration
_tool_instance = FirecrawlTool()

def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web for information."""
    return _tool_instance.web_search(query, max_results)

def scrape_webpage(url: str) -> Dict[str, Any]:
    """Extract content from a webpage."""
    return _tool_instance.scrape_content(url)

def batch_scrape_urls(urls: List[str]) -> List[Dict[str, Any]]:
    """Scrape multiple URLs efficiently."""
    return _tool_instance.batch_scrape(urls)

def search_and_summarize(query: str) -> Dict[str, Any]:
    """Search the web and provide summaries of results."""
    return _tool_instance.search_and_summarize(query)