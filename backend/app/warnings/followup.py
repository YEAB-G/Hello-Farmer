"""Warning follow-up loop: explains active warnings to returning callers."""
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Farmer, FarmerWarning, Warning


async def get_latest_farmer_warning(
    caller_hash: str,
    session: AsyncSession,
) -> Warning | None:
    """Retrieve the most recent warning delivered to a caller by their phone hash."""
    stmt = (
        select(Warning)
        .join(FarmerWarning, Warning.id == FarmerWarning.warning_id)
        .join(Farmer, FarmerWarning.farmer_id == Farmer.id)
        .where(Farmer.phone_hash == caller_hash)
        .order_by(desc(FarmerWarning.delivered_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def explain_warning_to_caller(warning: Warning | None, language: str = "am") -> str:
    """Generate spoken explanation and guidance for a previously received warning."""
    if not warning:
        if language == "om":
            return "Galmee keessan irratti akeekkachiisni haaraan hin jiru. Gaaffii biraa qabduu?"
        return "በመረጃዎ ላይ የተመዘገበ የቅርብ ጊዜ ማስጠንቀቂያ የለም። ሌላ ምን ልርዳዎት?"

    loc = warning.target_woreda or "አካባቢዎ"
    sev = warning.severity

    if language == "om":
        return (
            f"Naannoo {loc}tti akeekkachiisni rooba cimaa sadarkaa {sev} kennamee ture. "
            f"Bishaan kuullamuun sanyii fi midhaan akka hin miineef bo'oo lolaa baasaa. "
            f"Ogeessa qonnaa mariisisaa."
        )
    else:
        return (
            f"በ{loc} አካባቢ የ{sev} ደረጃ የከባድ ዝናብ ማስጠንቀቂያ ወጥቶ ነበር። "
            f"የውሃ ማቆር ሰብልዎን እንዳይጎዳው የማሳ ማስተንፈሻ ቦይ ያውጡና "
            f"የአካባቢዎን የልማት ጣቢያ ባለሙያ ያማክሩ።"
        )
