"""
Items CRUD router.

Provides full Create / Read / Update / Delete operations for cloud resource
items, backed by an in-memory dictionary.  Sample data is pre-populated at
module load time.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.models import Item, ItemCreate, ItemUpdate

router = APIRouter(prefix="/api/v1/items", tags=["Items"])

# ---------------------------------------------------------------------------
# In-memory data store
# ---------------------------------------------------------------------------

#: Primary store: UUID → Item
items_db: dict[UUID, Item] = {}


def _populate_sample_items() -> None:
    """Pre-populate the database with representative cloud resource items."""
    samples: list[dict] = [
        {
            "name": "m5.xlarge EC2 Instance",
            "description": "General-purpose compute instance with 4 vCPUs and 16 GB RAM.",
            "price": 0.192,
            "tags": ["compute", "aws", "ec2", "general-purpose"],
        },
        {
            "name": "RDS PostgreSQL db.r6g.large",
            "description": "Managed relational database — 2 vCPUs, 16 GB RAM, Multi-AZ.",
            "price": 0.26,
            "tags": ["database", "aws", "rds", "postgresql"],
        },
        {
            "name": "S3 Standard Storage (per GB)",
            "description": "Object storage with 11 nines of durability.",
            "price": 0.023,
            "tags": ["storage", "aws", "s3", "object-storage"],
        },
        {
            "name": "Azure Standard_D4s_v3 VM",
            "description": "4 vCPUs, 16 GB RAM — general-purpose Azure virtual machine.",
            "price": 0.192,
            "tags": ["compute", "azure", "vm", "general-purpose"],
        },
        {
            "name": "GKE e2-standard-4 Node",
            "description": "Google Kubernetes Engine worker node — 4 vCPUs, 16 GB RAM.",
            "price": 0.134,
            "tags": ["compute", "gcp", "kubernetes", "gke"],
        },
    ]

    for sample in samples:
        item = Item(
            id=uuid.uuid4(),
            name=sample["name"],
            description=sample["description"],
            price=sample["price"],
            tags=sample["tags"],
            created_at=datetime.utcnow(),
        )
        items_db[item.id] = item


# Pre-populate on import
_populate_sample_items()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[Item],
    summary="List all items",
    description="Returns a paginated list of items, optionally filtered by tag.",
)
async def list_items(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    tag: Optional[str] = Query(default=None, description="Filter by exact tag match"),
) -> list[Item]:
    """List items with optional pagination and tag filtering.

    Args:
        skip:  Records to skip (for pagination).
        limit: Maximum number of records to return.
        tag:   When supplied, only items whose ``tags`` list contains this
               value are returned.

    Returns:
        A list of :class:`Item` objects.
    """
    items = list(items_db.values())
    if tag:
        items = [i for i in items if tag in i.tags]
    return items[skip : skip + limit]


@router.post(
    "",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
)
async def create_item(payload: ItemCreate) -> Item:
    """Create and persist a new cloud resource item.

    Args:
        payload: The item creation payload.

    Returns:
        The newly created :class:`Item` with a generated UUID.
    """
    item = Item(
        id=uuid.uuid4(),
        name=payload.name,
        description=payload.description,
        price=payload.price,
        tags=payload.tags,
        created_at=datetime.utcnow(),
    )
    items_db[item.id] = item
    return item


@router.get(
    "/{item_id}",
    response_model=Item,
    summary="Get a single item by ID",
)
async def get_item(item_id: UUID) -> Item:
    """Retrieve a single item by its UUID.

    Args:
        item_id: The item's unique identifier.

    Returns:
        The :class:`Item` if found.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    item = items_db.get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found.",
        )
    return item


@router.put(
    "/{item_id}",
    response_model=Item,
    summary="Full item update",
    description="Replaces all mutable fields on the item.",
)
async def update_item(item_id: UUID, payload: ItemCreate) -> Item:
    """Perform a full replacement update of an existing item.

    Args:
        item_id: The item to update.
        payload: New field values (all fields are required).

    Returns:
        The updated :class:`Item`.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    existing = items_db.get(item_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found.",
        )

    updated = Item(
        id=existing.id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        tags=payload.tags,
        created_at=existing.created_at,
    )
    items_db[item_id] = updated
    return updated


@router.patch(
    "/{item_id}",
    response_model=Item,
    summary="Partial item update",
    description="Updates only the supplied fields, leaving others unchanged.",
)
async def patch_item(item_id: UUID, payload: ItemUpdate) -> Item:
    """Partially update an existing item.

    Only fields that are explicitly set in *payload* are modified.

    Args:
        item_id: The item to patch.
        payload: Fields to update (all optional).

    Returns:
        The patched :class:`Item`.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    existing = items_db.get(item_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found.",
        )

    # model_dump(exclude_unset=True) returns only explicitly supplied fields
    update_data = payload.model_dump(exclude_unset=True)
    updated = existing.model_copy(update=update_data)
    items_db[item_id] = updated
    return updated


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
)
async def delete_item(item_id: UUID) -> None:
    """Delete a cloud resource item permanently.

    Args:
        item_id: The item to delete.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found.",
        )
    del items_db[item_id]
