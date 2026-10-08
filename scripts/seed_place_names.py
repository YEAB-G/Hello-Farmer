"""Seed place_names table in PostgreSQL."""
import asyncio
import logging

from app.weather.location import seed_place_names_if_empty

logging.basicConfig(level=logging.INFO)


async def main():
    print("Checking and seeding Ethiopian place names...")
    count = await seed_place_names_if_empty()
    print(f"Successfully processed place names: {count} new places inserted.")


if __name__ == "__main__":
    asyncio.run(main())
