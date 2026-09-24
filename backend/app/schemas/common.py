"""Shared API schemas: pagination params and paged responses."""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class PageParams:
    """Validated ?page=&page_size= query parameters (used via Depends)."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number, starting at 1"),
        page_size: int = Query(
            DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"
        ),
    ) -> None:
        self.page = page
        self.page_size = page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
