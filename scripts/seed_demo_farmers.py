"""Seed synthetic demo farmers in PostgreSQL for warning targeting evaluation."""
import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import delete

from app.database.models import Farmer, FarmerContext, FarmerCrop
from app.database.session import async_session_factory
from app.farmer_context.profile import encrypt_phone_number, hash_phone_number

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_demo_farmers")

DEMO_FARMERS = [
    {
        "phone": "+251911000001",
        "woreda": "Adama",
        "region": "Oromia",
        "crop": "teff",
        "lang": "am",
        "opted_in": True,
    },
    {
        "phone": "+251911000002",
        "woreda": "Adama",
        "region": "Oromia",
        "crop": "maize",
        "lang": "om",
        "opted_in": True,
    },
    {
        "phone": "+251911000003",
        "woreda": "Adama",
        "region": "Oromia",
        "crop": "wheat",
        "lang": "am",
        "opted_in": False,  # Not opted in (must be excluded)
    },
    {
        "phone": "+251911000004",
        "woreda": "Bishoftu",
        "region": "Oromia",
        "crop": "teff",
        "lang": "am",
        "opted_in": True,
    },
    {
        "phone": "+251911000005",
        "woreda": "Bishoftu",
        "region": "Oromia",
        "crop": "wheat",
        "lang": "om",
        "opted_in": True,
    },
    {
        "phone": "+251911000006",
        "woreda": "Asella",
        "region": "Oromia",
        "crop": "wheat",
        "lang": "om",
        "opted_in": True,
    },
    {
        "phone": "+251911000007",
        "woreda": "Asella",
        "region": "Oromia",
        "crop": "barley",
        "lang": "am",
        "opted_in": False,  # Not opted in
    },
    {
        "phone": "+251911000008",
        "woreda": "Ambo",
        "region": "Oromia",
        "crop": "maize",
        "lang": "om",
        "opted_in": True,
    },
    {
        "phone": "+251911000009",
        "woreda": "Hawassa",
        "region": "Sidama",
        "crop": "coffee",
        "lang": "am",
        "opted_in": True,
    },
    {
        "phone": "+251911000010",
        "woreda": "Hawassa",
        "region": "Sidama",
        "crop": "teff",
        "lang": "am",
        "opted_in": False,
    },
]


async def seed_farmers() -> int:
    """Insert or update 10 synthetic demo farmers in PostgreSQL."""
    async with async_session_factory() as session:
        count = 0
        for item in DEMO_FARMERS:
            p_hash = hash_phone_number(item["phone"])
            # Remove existing demo record if present
            await session.execute(delete(Farmer).where(Farmer.phone_hash == p_hash))

            farmer_id = str(uuid.uuid4())
            farmer = Farmer(
                id=farmer_id,
                phone_hash=p_hash,
                encrypted_phone=encrypt_phone_number(item["phone"]),
                preferred_language=item["lang"],
                is_opted_in_warnings=item["opted_in"],
                created_at=datetime.utcnow(),
            )
            session.add(farmer)

            context = FarmerContext(
                id=str(uuid.uuid4()),
                farmer_id=farmer_id,
                current_crop=item["crop"],
                woreda=item["woreda"],
                region=item["region"],
                updated_at=datetime.utcnow(),
            )
            session.add(context)

            crop_rec = FarmerCrop(
                id=str(uuid.uuid4()),
                farmer_id=farmer_id,
                crop_name=item["crop"],
                created_at=datetime.utcnow(),
            )
            session.add(crop_rec)
            count += 1

        await session.commit()
        logger.info(f"Seeded {count} synthetic demo farmers.")
        return count


if __name__ == "__main__":
    asyncio.run(seed_farmers())
