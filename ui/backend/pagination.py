"""
Pagination Utilities for Azure Cost Optimizer API

Provides helper functions for paginating list responses in Flask APIs.

Usage:
    from pagination import paginate, PaginatedResponse

    @app.route('/api/items')
    def get_items():
        items = get_all_items()  # Could be a large list
        return paginate(items, request)
"""

from flask import Request, jsonify
from typing import Any, List, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass
import math

T = TypeVar('T')


@dataclass
class PaginationParams:
    """Extracted pagination parameters from a request."""
    page: int = 1
    per_page: int = 25
    sort_by: Optional[str] = None
    sort_order: str = 'asc'
    
    # Limits to prevent abuse
    MAX_PER_PAGE = 100
    DEFAULT_PER_PAGE = 25
    
    @classmethod
    def from_request(cls, request: Request) -> 'PaginationParams':
        """
        Extract pagination parameters from a Flask request.
        
        Query params:
            page: Page number (1-indexed), default 1
            per_page: Items per page, default 25, max 100
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'
        """
        try:
            page = max(1, int(request.args.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        
        try:
            per_page = min(
                cls.MAX_PER_PAGE,
                max(1, int(request.args.get('per_page', cls.DEFAULT_PER_PAGE)))
            )
        except (ValueError, TypeError):
            per_page = cls.DEFAULT_PER_PAGE
        
        sort_by = request.args.get('sort_by')
        sort_order = request.args.get('sort_order', 'asc').lower()
        if sort_order not in ('asc', 'desc'):
            sort_order = 'asc'
        
        return cls(
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )


@dataclass
class PaginatedResponse:
    """
    Paginated response structure.
    
    Includes:
    - items: The current page of items
    - pagination: Metadata about the pagination state
    """
    items: List[Any]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'items': self.items,
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages,
                'has_next': self.has_next,
                'has_prev': self.has_prev,
            }
        }
    
    def to_response(self):
        """Convert to Flask JSON response."""
        return jsonify(self.to_dict())


def paginate(
    items: List[Any],
    request: Request,
    sort_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Paginate a list of items based on request parameters.
    
    Args:
        items: Full list of items to paginate
        request: Flask request object (used to extract query params)
        sort_key: Default field to sort by if not specified in request
        
    Returns:
        Dictionary with 'items' and 'pagination' keys
        
    Example:
        @app.route('/api/resources')
        def list_resources():
            all_resources = get_all_resources()
            return jsonify(paginate(all_resources, request, sort_key='name'))
    """
    params = PaginationParams.from_request(request)
    
    # Apply sorting if requested or if a default sort key is provided
    sort_by = params.sort_by or sort_key
    if sort_by and items:
        try:
            reverse = params.sort_order == 'desc'
            # Handle both dict items and objects with attributes
            if isinstance(items[0], dict):
                items = sorted(items, key=lambda x: x.get(sort_by, ''), reverse=reverse)
            else:
                items = sorted(items, key=lambda x: getattr(x, sort_by, ''), reverse=reverse)
        except (TypeError, AttributeError):
            # If sorting fails, continue without sorting
            pass
    
    # Calculate pagination
    total = len(items)
    total_pages = math.ceil(total / params.per_page) if params.per_page > 0 else 0
    
    # Ensure page is within bounds
    page = min(params.page, max(1, total_pages))
    
    # Slice the items
    start = (page - 1) * params.per_page
    end = start + params.per_page
    page_items = items[start:end]
    
    return PaginatedResponse(
        items=page_items,
        total=total,
        page=page,
        per_page=params.per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    ).to_dict()


def paginate_query_result(
    query_func,
    request: Request,
    transform_func=None
) -> Dict[str, Any]:
    """
    Paginate results from a function that returns a list.
    
    This is useful when the data comes from an API call or database query.
    
    Args:
        query_func: Function that returns the full list of items
        request: Flask request object
        transform_func: Optional function to transform each item
        
    Returns:
        Paginated response dictionary
    """
    items = query_func()
    
    if transform_func:
        items = [transform_func(item) for item in items]
    
    return paginate(items, request)


# Convenience function for creating pagination links (for HATEOAS)
def create_pagination_links(
    base_url: str,
    page: int,
    total_pages: int,
    per_page: int
) -> Dict[str, Optional[str]]:
    """
    Create pagination links for HATEOAS-style responses.
    
    Args:
        base_url: Base URL for the endpoint
        page: Current page number
        total_pages: Total number of pages
        per_page: Items per page
        
    Returns:
        Dictionary with 'first', 'prev', 'next', 'last' URLs
    """
    def make_url(p: int) -> str:
        return f"{base_url}?page={p}&per_page={per_page}"
    
    return {
        'first': make_url(1),
        'prev': make_url(page - 1) if page > 1 else None,
        'next': make_url(page + 1) if page < total_pages else None,
        'last': make_url(total_pages) if total_pages > 0 else make_url(1),
    }
