import asyncio
import uuid
import hashlib
from datetime import datetime, timedelta
import random

from app.database.session import async_session_factory
from app.database.models import Call, ConversationMessage

SAMPLE_CALLS = [
    {
        "caller": "251911234567",
        "lang": "am",
        "crop": "ስንዴ (Wheat)",
        "duration": 94,
        "days_ago": 1,
        "end_reason": "completed",
        "turns": [
            ("caller", "ጤና ይስጥልኝ፣ የስንዴ ቢጫ ዝገት (Yellow Rust) በሽታ ቅጠሎቹ ላይ አይቻለሁ፤ እንዴት መከላከል እችላለሁ?"),
            ("assistant", "ጤና ይስጥልኝ አርሶ አደር። የስንዴ ቢጫ ዝገት የፈንገስ በሽታ ሲሆን ቅጠሉ ላይ ቢጫ ዱቄት መሰል ነጠብጣብ ያሳያል። ፈንገስ ኬሚካል (Tilt ወይም Rex Duo) በሄክታር ግማሽ ሊትር ከውሃ ጋር ቀላቅለው በማለዳ ይርጩ። እርጥበት ካለ ይቆጠቡ።"),
            ("caller", "በጣም አመሰግናለሁ፣ የት ማግኘት እችላለሁ?"),
            ("assistant", "በአካባቢዎ በሚገኘው የግብርና ጽሕፈት ቤት ወይም የገበሬዎች ህብረት ስራ ማህበር መደብር ማግኘት ይችላሉ። መልካም ምርት!")
        ]
    },
    {
        "caller": "251922345678",
        "lang": "om",
        "crop": "Boqqoolloo (Maize)",
        "duration": 122,
        "days_ago": 2,
        "end_reason": "completed",
        "turns": [
            ("caller", "Akkam jirtu, boqqoolloo koo irratti raammoo buqqee (fall armyworm) argeera, qorichi isaa maali?"),
            ("assistant", "Akkam jirtu qotee bulaa. Raammoo aramaa (Fall Armyworm) ittisuuf dafee qoricha biifuu qabdu. Qoricha akka Ampligo ykn Karate Zeon fayyadamuu dandeessu. Ganama ykn galgala qabbanaatti biifaa."),
            ("caller", "Galatoomaa, deebii gaarii dha.")
        ]
    },
    {
        "caller": "251933456789",
        "lang": "am",
        "crop": "ጤፍ (Teff)",
        "duration": 85,
        "days_ago": 3,
        "end_reason": "completed",
        "turns": [
            ("caller", "የጤፍ ዘር ለመዝራት ምርጥ የማዳበሪያ መጠን ስንት ነው?"),
            ("assistant", "ለጤፍ ምርጥ የሆነው NPSB ማዳበሪያ በሄክታር 100 ኪ.ግ እና ዩሪያ 50 ኪ.ግ ሲሆን ዩሪያውን ከዘራ ከ30-40 ቀናት በኋላ በአረም ወቅት መስጠት ይመረጣል።"),
            ("caller", "እሺ ገብቶኛል አመሰግናለሁ።")
        ]
    },
    {
        "caller": "251944567890",
        "lang": "om",
        "crop": "Buna (Coffee)",
        "duration": 110,
        "days_ago": 4,
        "end_reason": "completed",
        "turns": [
            ("caller", "Biqiltuu bunaatiif xaa'oon kamtu filatamaadha?"),
            ("assistant", "Biqiltuu bunaatiif xaa'oo kompoostii (uumamaa) fayyadamuun filatamaadha. Kana malees xaa'oo NPSB xiqqeessanii naquun guddina isaatiif gaariidha."),
        ]
    },
    {
        "caller": "251955678901",
        "lang": "am",
        "crop": "ቲማቲም (Tomato)",
        "duration": 45,
        "days_ago": 5,
        "end_reason": "caller_hangup",
        "turns": [
            ("caller", "የቲማቲም ቅጠል መድረቅ በሽታ ምልክቶች ምንድን ናቸው?"),
            ("assistant", "የቲማቲም ቅጠል መድረቅ (Blight) በቅጠሎች ጫፍ ላይ ጥቁር ወይም ቡናማ ነጠብጣቦች በመፍጠር ቶሎ እንዲደርቁ ያደርጋል።"),
        ]
    },
    {
        "caller": "251966789012",
        "lang": "am",
        "crop": "ገብስ (Barley)",
        "duration": 18,
        "days_ago": 6,
        "end_reason": "max_silence",
        "turns": [
            ("assistant", "ጤና ይስጥልኝ! ሄሎ ፋርመር ነኝ። እንዴት ልርዳዎት?"),
        ]
    },
    {
        "caller": "251977890123",
        "lang": "om",
        "crop": "Qamadii (Wheat)",
        "duration": 78,
        "days_ago": 7,
        "end_reason": "completed",
        "turns": [
            ("caller", "Qamadii irratti aramaa ittisuuf qoricha kamtu gaariidha?"),
            ("assistant", "Aramaa baala bal'aa qabuuf 2,4-D amine fayyadamuun ni danda'ama. Akkaata ajaja qorichichaatti fayyadamaa."),
            ("caller", "Galatoomaa!")
        ]
    },
    {
        "caller": "251988901234",
        "lang": "am",
        "crop": "ስንዴ (Wheat)",
        "duration": 135,
        "days_ago": 8,
        "end_reason": "completed",
        "turns": [
            ("caller", "አፈሬ ጥቁር አፈር ነው፣ ስንዴ ከመዝራቴ በፊት ምን ማድረግ አለብኝ?"),
            ("assistant", "ጥቁር አፈር ውሃ የመቋጠር ባህሪ ስላለው የፍሳሽ ቦይ (BBM) ማዘጋጀት በጣም አስፈላጊ ነው። ውሃ እንዳይተኛ በማድረግ ስር መበስበስን ይከላከላል።"),
            ("caller", "በጣም ጥሩ ምክር ነው፣ አመሰግናለሁ።")
        ]
    },
    {
        "caller": "251999012345",
        "lang": "om",
        "crop": "Boqqoolloo (Maize)",
        "duration": 92,
        "days_ago": 9,
        "end_reason": "completed",
        "turns": [
            ("caller", "Roobni guddaan dhufeera, boqqoolloon koo hin manca'aa?"),
            ("assistant", "Rooba cimaa booda bishaan lolaa lafa qonnaa keessaa yaasuuf bo'oo dhangala'aa banuun barbaachisaadha. Bishaan yoo ciise hidda ni tortorsa."),
        ]
    },
    {
        "caller": "251911112233",
        "lang": "am",
        "crop": "ጤፍ (Teff)",
        "duration": 60,
        "days_ago": 10,
        "end_reason": "completed",
        "turns": [
            ("caller", "የማግኛ ኬሚካል ለጤፍ አረም ማጥፊያ ስንት ሊትር ነው?"),
            ("assistant", "ለጤፍ ሰፊ ቅጠል አረሞች 2,4-D በሄክታር አንድ ሊትር በ200 ሊትር ውሃ በጥብጠው ይርጩ። ጤፉ ከ3-4 ቅጠል ባወጣበት ወቅት ቢሆን ይመረጣል።"),
        ]
    },
]

async def seed_calls():
    async with async_session_factory() as session:
        for item in SAMPLE_CALLS:
            caller_hash = hashlib.sha256(item["caller"].encode()).hexdigest()
            call_id = str(uuid.uuid4())
            call_start = datetime.utcnow() - timedelta(days=item["days_ago"], hours=random.randint(1, 10))
            call_end = call_start + timedelta(seconds=item["duration"])
            
            call = Call(
                id=call_id,
                caller_hash=caller_hash,
                is_first_time=False,
                language=item["lang"],
                reached_answer=(item["end_reason"] == "completed"),
                fallback_used=False,
                end_reason=item["end_reason"],
                time_to_first_answer_ms=1800,
                duration_seconds=item["duration"],
                started_at=call_start,
                ended_at=call_end,
            )
            session.add(call)

            for spk, txt in item["turns"]:
                msg = ConversationMessage(
                    id=str(uuid.uuid4()),
                    call_id=call_id,
                    speaker=spk,
                    text=txt,
                    created_at=call_start + timedelta(seconds=random.randint(5, max(6, item["duration"] - 5))),
                )
                session.add(msg)

        await session.commit()
        print(f"Successfully seeded {len(SAMPLE_CALLS)} realistic calls with full dialogue history.")

if __name__ == "__main__":
    asyncio.run(seed_calls())
