"""
Base class for deal sources.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class DealSource(ABC):
    """Abstract base class for deal data sources."""
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this source."""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the type of source (e.g., 'sec', 'press_release')."""
        pass
    
    @abstractmethod
    def search_deals(
        self,
        company_names: Optional[List[str]] = None,
        company_ciks: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        deal_types: Optional[List[str]] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for deals from this source.
        
        Args:
            company_names: Filter by company names
            company_ciks: Filter by SEC CIK numbers
            from_date: Start date for search
            to_date: End date for search
            deal_types: Filter by deal types
            max_results: Maximum results to return
        
        Returns:
            List of raw deal records from the source
        """
        pass
    
    @abstractmethod
    def parse_deal(self, raw_deal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a raw deal record into structured format.
        
        Args:
            raw_deal: Raw deal data from the source
        
        Returns:
            Parsed deal data with standard fields, or None if parsing fails
        """
        pass
    
    def is_enabled(self) -> bool:
        """Check if this source is enabled and configured."""
        return False
