"""Create a supplier and an API key, then print the key (shown once).

Usage:  py scripts/seed.py "Acme Supplies"

Copy the printed key into the X-API-Key header when calling the API.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.dao.api_key_dao import ApiKeyDAO  # noqa: E402
from app.dao.supplier_dao import SupplierDAO  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.utils.security import generate_api_key, hash_api_key, key_prefix  # noqa: E402


async def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "Demo Supplier"

    async with SessionLocal() as session:
        supplier = await SupplierDAO(session).create(name=name)
        plaintext = generate_api_key()
        await ApiKeyDAO(session).create(
            supplier_id=supplier.id,
            key_prefix=key_prefix(plaintext),
            key_hash=hash_api_key(plaintext),
            label="seed",
        )
        await session.commit()

    print("Supplier created.")
    print(f"  supplier_id : {supplier.id}")
    print(f"  name        : {name}")
    print(f"  API key     : {plaintext}")
    print("\nSave the API key now — it is not stored in plaintext and won't be shown again.")
    print('Use it as a header:  X-API-Key: <key>')


if __name__ == "__main__":
    asyncio.run(main())
