"""
Paper resolution and processing service.

This service handles paper identification, full-text resolution, and metadata
extraction from various academic sources.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import resolvers from the utils directory (will be migrated to resolvers/)
from utils.full_text_resolver import (
    resolve_full_text,
    extract_pmid_from_query,
    extract_doi_from_query,
    search_paper_by_title,
    validate_doi,
    validate_pmid
)

logger = logging.getLogger(__name__)

@dataclass
class PaperResult:
    """Container for paper resolution results."""
    title: str = ""
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    abstract: str = ""
    full_text: str = ""
    authors: List[str] = None
    journal: str = ""
    year: str = ""
    pdf_url: str = ""
    source: str = ""
    access_status: str = ""
    access_logs: List[str] = None
    has_full_text: bool = False
    has_abstract: bool = False
    text_length: int = 0
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.access_logs is None:
            self.access_logs = []
    
    @property
    def has_content(self) -> bool:
        """Check if any content (abstract or full text) is available."""
        return bool(self.abstract or self.full_text)
    
    @property
    def primary_text(self) -> str:
        """Get the primary text content (full text if available, otherwise abstract)."""
        return self.full_text if self.full_text else self.abstract
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'doi': self.doi,
            'pmid': self.pmid,
            'pmcid': self.pmcid,
            'authors': self.authors,
            'journal': self.journal,
            'year': self.year,
            'pdf_url': self.pdf_url,
            'source': self.source,
            'access_status': self.access_status,
            'access_logs': self.access_logs,
            'has_full_text': self.has_full_text,
            'has_abstract': self.has_abstract,
            'has_content': self.has_content,
            'text_length': self.text_length
        }

class PaperService:
    """Service for paper resolution and processing."""
    
    def __init__(self, max_text_length: int = 10000):
        """
        Initialize paper service.
        
        Args:
            max_text_length: Maximum length of text to include in prompts
        """
        self.max_text_length = max_text_length
    
    def process_query(self, query: str) -> PaperResult:
        """
        Process a user query to extract and resolve paper information.
        
        Args:
            query: User input query
            
        Returns:
            PaperResult with resolved paper information
        """
        logger.info(f"Processing query: {query[:100]}...")
        
        # Initialize result
        result = PaperResult()
        
        # Try to extract DOI or PMID from the query
        doi = extract_doi_from_query(query)
        pmid = extract_pmid_from_query(query)
        
        if doi:
            logger.info(f"Found DOI in query: {doi}")
            result.doi = doi
        if pmid:
            logger.info(f"Found PMID in query: {pmid}")
            result.pmid = pmid
        
        # If no identifiers found, try to find paper by title
        if not (doi or pmid) and len(query) > 20:
            title = self._extract_title_from_query(query)
            if title:
                logger.info(f"Attempting to find paper with title: {title}")
                found_doi, found_pmid = search_paper_by_title(title)
                if found_doi or found_pmid:
                    result.doi = found_doi or result.doi
                    result.pmid = found_pmid or result.pmid
                    result.title = title
        
        # Resolve paper content if identifiers are available
        if result.doi or result.pmid:
            self._resolve_paper_content(result)
        
        return result
    
    def resolve_paper(self, doi: str = None, pmid: str = None, 
                     title: str = None, pmcid: str = None) -> PaperResult:
        """
        Resolve paper information from explicit identifiers.
        
        Args:
            doi: Digital Object Identifier
            pmid: PubMed ID
            title: Paper title
            pmcid: PubMed Central ID
            
        Returns:
            PaperResult with resolved information
        """
        result = PaperResult(doi=doi or "", pmid=pmid or "", 
                           title=title or "", pmcid=pmcid or "")
        
        # If title provided but no identifiers, try to find them
        if title and not (doi or pmid):
            found_doi, found_pmid = search_paper_by_title(title)
            result.doi = found_doi or result.doi
            result.pmid = found_pmid or result.pmid
        
        # Resolve content
        if result.doi or result.pmid or result.pmcid:
            self._resolve_paper_content(result)
        
        return result
    
    def _extract_title_from_query(self, query: str) -> Optional[str]:
        """Extract potential paper title from query."""
        import re
        
        title_patterns = [
            r'titled "([^"]+)"',
            r'titled: ([^\.]+)',
            r'publication ([^\.]+)',
            r'paper ([^\.]+)',
            r'article ([^\.]+)',
            r'titled (?!.*doi)([^\.]+)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                potential_title = (
                    match.group(1)
                    .strip()
                    .replace('titled ', '')
                    .replace('publication ', '')
                    .replace('paper ', '')
                    .replace('article ', '')
                    .strip('" ')
                )
                if len(potential_title) > 10:  # Reasonable title length
                    return potential_title
        
        return None
    
    def _resolve_paper_content(self, result: PaperResult) -> None:
        """Resolve full text and metadata for a paper."""
        try:
            logger.info(f"Resolving content for DOI: {result.doi}, PMID: {result.pmid}")
            
            # Use the existing resolver
            resolution_result = resolve_full_text(
                pmid=result.pmid if result.pmid else None,
                doi=result.doi if result.doi else None,
                title=result.title if result.title else None
            )
            
            full_text = resolution_result.get('text') if resolution_result else None
            metadata = resolution_result if resolution_result else {}
            
            if full_text:
                # Determine if it's full text or abstract
                result.has_full_text = metadata.get('has_full_text', False)
                result.has_abstract = bool(full_text) and not result.has_full_text
                
                # Truncate if necessary
                if len(full_text) > self.max_text_length:
                    result.full_text = full_text[:self.max_text_length] + "...[truncated]"
                    result.text_length = len(full_text)
                else:
                    if result.has_full_text:
                        result.full_text = full_text
                    else:
                        result.abstract = full_text
                    result.text_length = len(full_text)
                
                # Set access status
                if result.has_full_text:
                    result.access_status = "Full Text Available"
                else:
                    result.access_status = "Abstract Only"
            else:
                result.access_status = "No Content Available"
            
            # Extract metadata
            if isinstance(metadata, dict):
                result.title = metadata.get('title', result.title)
                result.authors = metadata.get('authors', [])
                result.journal = metadata.get('journal', '')
                result.year = str(metadata.get('year', ''))
                result.pdf_url = metadata.get('pdf_url', '')
                result.source = metadata.get('source', '')
                result.access_logs = metadata.get('access_logs', [])
                
                # Update identifiers from metadata
                result.doi = metadata.get('doi', result.doi)
                result.pmid = metadata.get('pmid', result.pmid)
            
        except Exception as e:
            logger.error(f"Error resolving paper content: {e}")
            result.access_status = f"Error: {str(e)}"
    
    def build_enhanced_prompt(self, original_query: str, paper_result: PaperResult) -> str:
        """
        Build an enhanced prompt with paper context.
        
        Args:
            original_query: Original user query
            paper_result: Resolved paper information
            
        Returns:
            Enhanced prompt with paper context
        """
        if not paper_result.has_content:
            return original_query
        
        context_parts = []
        
        # Add paper content
        primary_text = paper_result.primary_text
        if primary_text:
            content_type = "Full text" if paper_result.has_full_text else "Abstract"
            context_parts.append(f"{content_type} of the paper:\n{primary_text}")
        
        # Add metadata
        metadata_lines = []
        if paper_result.title:
            metadata_lines.append(f"Title: {paper_result.title}")
        if paper_result.authors:
            metadata_lines.append(f"Authors: {', '.join(paper_result.authors)}")
        if paper_result.journal:
            metadata_lines.append(f"Journal: {paper_result.journal}")
        if paper_result.year:
            metadata_lines.append(f"Year: {paper_result.year}")
        if paper_result.doi:
            metadata_lines.append(f"DOI: {paper_result.doi}")
        
        if metadata_lines:
            context_parts.append("Paper metadata:\n" + "\n".join(metadata_lines))
        
        # Build final prompt
        enhanced_prompt = (
            f"I'd like you to analyze this scientific paper:\n\n"
            + "\n\n".join(context_parts)
            + "\n\n"
            + f"Based on this paper, please answer the following question: {original_query}"
        )
        
        return enhanced_prompt
    
    def test_all_sources(self, doi: Optional[str] = None, pmid: Optional[str] = None, 
                        title: Optional[str] = None, pmcid: Optional[str] = None) -> Dict[str, Any]:
        """
        Test all available sources for paper access.
        
        Args:
            doi: DOI to test
            pmid: PMID to test
            title: Paper title to test
            pmcid: PMC ID to test
            
        Returns:
            Dictionary containing test results for each source
        """
        results = {}
        
        # Test different resolvers
        test_cases = [
            ("DOI Resolver", lambda: self._test_doi_resolver(doi) if doi else None),
            ("PMID Resolver", lambda: self._test_pmid_resolver(pmid) if pmid else None),
            ("Title Search", lambda: self._test_title_search(title) if title else None),
            ("Enhanced Resolver", lambda: self._test_enhanced_resolver(doi, pmid, title))
        ]
        
        for test_name, test_func in test_cases:
            try:
                result = test_func()
                if result is not None:
                    results[test_name] = {
                        "status": "success" if result.has_content else "no_content",
                        "title": result.title,
                        "doi": result.doi,
                        "pmid": result.pmid,
                        "has_full_text": result.has_full_text,
                        "text_length": result.text_length,
                        "source": result.source,
                        "access_logs": result.access_logs
                    }
                else:
                    results[test_name] = {"status": "skipped", "reason": "No input provided"}
            except Exception as e:
                results[test_name] = {"status": "error", "error": str(e)}
        
        return results
    
    def _test_doi_resolver(self, doi: str) -> Optional[PaperResult]:
        """Test DOI-based resolution."""
        if not doi:
            return None
        return self.resolve_paper(doi=doi)
    
    def _test_pmid_resolver(self, pmid: str) -> Optional[PaperResult]:
        """Test PMID-based resolution.""" 
        if not pmid:
            return None
        return self.resolve_paper(pmid=pmid)
    
    def _test_title_search(self, title: str) -> Optional[PaperResult]:
        """Test title-based search."""
        if not title:
            return None
        return self.resolve_paper(title=title)
    
    def _test_enhanced_resolver(self, doi: Optional[str], pmid: Optional[str], 
                               title: Optional[str]) -> PaperResult:
        """Test the enhanced resolver with all available information."""
        return self.resolve_paper(doi=doi, pmid=pmid, title=title)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on paper resolution services.
        
        Returns:
            Dictionary containing health status
        """
        health_status = {
            'overall_status': 'healthy',
            'resolvers': {},
            'dependencies': {}
        }
        
        # Test basic functionality
        try:
            # Test DOI validation
            valid_doi = validate_doi("10.1038/nature12373")
            health_status['dependencies']['doi_validation'] = 'healthy' if valid_doi else 'unhealthy'
            
            # Test PMID validation
            valid_pmid = validate_pmid("23851565")
            health_status['dependencies']['pmid_validation'] = 'healthy' if valid_pmid else 'unhealthy'
            
            # Test basic paper search functionality
            test_result = self.process_query("10.1038/nature12373")
            health_status['resolvers']['basic_resolution'] = 'healthy' if test_result else 'unhealthy'
            
        except Exception as e:
            health_status['overall_status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status
