"""
Centralized logging service for structured application logging.
"""

import os
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import Config

logger = logging.getLogger(__name__)


class LoggingService:
    """Service for structured application logging."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize logging service.
        
        Args:
            log_dir: Directory for log files (defaults to Config.LOG_DIR)
        """
        self.log_dir = log_dir or Config.LOG_DIR
        self.log_dir.mkdir(exist_ok=True)
        
        # Log file paths
        self.chat_log_file = self.log_dir / 'chat_logs.csv'
        self.metadata_log_file = self.log_dir / 'metadata_log.json'
        
        # Initialize CSV file with headers if it doesn't exist
        self._init_chat_log()
    
    def _init_chat_log(self):
        """Initialize chat log CSV file with headers if it doesn't exist."""
        if not self.chat_log_file.exists():
            with open(self.chat_log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'session_id', 'user_input', 'model', 
                    'paper_title', 'paper_doi', 'paper_pmid', 'has_full_text',
                    'response_length', 'error'
                ])
    
    def log_chat(self, session_id: str, user_input: str, response: str,
                 paper_info: Dict[str, Any], model: str, error: Optional[str] = None):
        """
        Log a chat interaction.
        
        Args:
            session_id: User session identifier
            user_input: User's input message
            response: AI model response
            paper_info: Dictionary containing paper metadata
            model: AI model used
            error: Error message if any
        """
        try:
            timestamp = datetime.now().isoformat()
            
            # Extract paper information safely
            paper_title = paper_info.get('title', '')
            paper_doi = paper_info.get('doi', '')
            paper_pmid = paper_info.get('pmid', '')
            has_full_text = paper_info.get('has_full_text', False)
            
            # Calculate response length
            response_length = len(response) if response else 0
            
            # Write to CSV log
            with open(self.chat_log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, session_id, user_input, model,
                    paper_title, paper_doi, paper_pmid, has_full_text,
                    response_length, error or ''
                ])
            
            logger.info(f"Chat interaction logged for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to log chat interaction: {e}")
    
    def log_metadata(self, session_id: str, metadata: Dict[str, Any]):
        """
        Log paper metadata to JSON file.
        
        Args:
            session_id: User session identifier
            metadata: Paper metadata dictionary
        """
        try:
            timestamp = datetime.now().isoformat()
            
            # Load existing metadata log or create new one
            metadata_log = []
            if self.metadata_log_file.exists():
                try:
                    with open(self.metadata_log_file, 'r', encoding='utf-8') as f:
                        metadata_log = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Corrupted metadata log file, starting fresh")
                    metadata_log = []
            
            # Add new entry
            log_entry = {
                'timestamp': timestamp,
                'session_id': session_id,
                'metadata': metadata
            }
            metadata_log.append(log_entry)
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(metadata_log) > 1000:
                metadata_log = metadata_log[-1000:]
            
            # Write back to file
            with open(self.metadata_log_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_log, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Metadata logged for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to log metadata: {e}")
    
    def get_recent_chats(self, limit: int = 100) -> list[Dict[str, Any]]:
        """
        Get recent chat interactions.
        
        Args:
            limit: Maximum number of chats to return
            
        Returns:
            List of chat dictionaries
        """
        chats = []
        try:
            if self.chat_log_file.exists():
                with open(self.chat_log_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    chats = list(reader)
                    
                # Return most recent chats
                return chats[-limit:]
                
        except Exception as e:
            logger.error(f"Failed to read chat log: {e}")
        
        return chats
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics from logs.
        
        Returns:
            Dictionary containing usage statistics
        """
        stats = {
            'total_chats': 0,
            'models_used': {},
            'papers_processed': 0,
            'success_rate': 0.0
        }
        
        try:
            chats = self.get_recent_chats(limit=10000)  # Get more for stats
            
            stats['total_chats'] = len(chats)
            
            if chats:
                # Count model usage
                for chat in chats:
                    model = chat.get('model', 'unknown')
                    stats['models_used'][model] = stats['models_used'].get(model, 0) + 1
                
                # Count papers with DOI/PMID
                papers_with_ids = sum(
                    1 for chat in chats 
                    if chat.get('paper_doi') or chat.get('paper_pmid')
                )
                stats['papers_processed'] = papers_with_ids
                
                # Calculate success rate (chats without errors)
                successful_chats = sum(1 for chat in chats if not chat.get('error'))
                stats['success_rate'] = successful_chats / len(chats) * 100
            
        except Exception as e:
            logger.error(f"Failed to calculate usage stats: {e}")
        
        return stats
    
    def get_chat_log_path(self) -> Path:
        """Get the path to the chat log file."""
        return self.chat_log_file
    
    def get_metadata_log_path(self) -> Path:
        """Get the path to the metadata log file."""
        return self.metadata_log_file
    
    def get_metadata_entries(self) -> list[Dict[str, Any]]:
        """Get all metadata entries."""
        try:
            if self.metadata_log_file.exists():
                with open(self.metadata_log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [entry.get('metadata', {}) for entry in data]
        except Exception as e:
            logger.error(f"Failed to read metadata entries: {e}")
        return []
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
