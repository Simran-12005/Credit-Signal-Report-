"""Shared FastAPI dependencies: DB session + API-key authentication."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.api_key_dao import ApiKeyDAO
from app.database import get_session
from app.utils.security import hash_api_key

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_supplier_id(
    session: SessionDep,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> UUID:
    """Authenticate the request by its X-API-Key header and return the supplier id.

    Every data-bearing endpoint depends on this, so all access is supplier-scoped.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
        )
    api_key = await ApiKeyDAO(session).get_active_by_hash(hash_api_key(x_api_key))
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key.",
        )
    return api_key.supplier_id


SupplierIdDep = Annotated[UUID, Depends(get_current_supplier_id)]
