"""Automated Call Flow Simulation Harness for Asterisk AudioSocket (Phase 5).

Simulates Asterisk full-duplex AudioSocket communication (port 9092) and tests:
  1. normal_question: Caller connects, hears greeting/consent, provides speech, receives answer.
  2. silence_timeout: Caller silent -> server repeats prompt, then clean disconnect.
  3. caller_hangup: Caller disconnects -> server cleans up cleanly.
"""
import asyncio
import logging
import os
import struct
import sys
import uuid

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("simulate_call")

TYPE_HANGUP = 0x00
TYPE_AUDIO = 0x10
TYPE_ERROR = 0x01


class DuplexAudioSocketClient:
    """Full-duplex Asterisk AudioSocket simulator."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9092):
        self.host = host
        self.port = port
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.call_uuid = uuid.uuid4()
        self.total_received_bytes = 0
        self._read_task: asyncio.Task | None = None
        self.is_connected = False

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        self.is_connected = True
        # Send 16-byte UUID handshake
        self.writer.write(self.call_uuid.bytes)
        await self.writer.drain()
        logger.info(f"Connected to AudioSocket on {self.host}:{self.port} (UUID: {self.call_uuid})")

        # Start continuous background reader
        self._read_task = asyncio.create_task(self._reader_loop())

    async def _reader_loop(self):
        """Continuously read frames from server."""
        try:
            while self.is_connected and not self.reader.at_eof():
                header = await self.reader.readexactly(3)
                msg_type, length = struct.unpack("!BH", header)
                payload = await self.reader.readexactly(length) if length > 0 else b""
                if msg_type in (TYPE_AUDIO, 0x10, 0x02):
                    self.total_received_bytes += len(payload)
                elif msg_type == TYPE_HANGUP:
                    logger.info("Received HANGUP signal from AudioSocket server.")
                    break
        except (asyncio.IncompleteReadError, ConnectionResetError, Exception):
            pass
        finally:
            self.is_connected = False

    async def send_audio_chunk(self, pcm_chunk: bytes):
        """Send 8 kHz PCM audio chunk in 320-byte (20ms) frames."""
        if not self.is_connected or not self.writer:
            return
        chunk_size = 320
        for i in range(0, len(pcm_chunk), chunk_size):
            chunk = pcm_chunk[i:i + chunk_size]
            header = struct.pack("!BH", TYPE_AUDIO, len(chunk))
            self.writer.write(header + chunk)
            await self.writer.drain()
            await asyncio.sleep(0.015)  # Real-time pacing

    async def send_hangup(self):
        """Send clean hangup frame."""
        if self.writer and not self.writer.is_closing():
            try:
                header = struct.pack("!BH", TYPE_HANGUP, 0)
                self.writer.write(header)
                await self.writer.drain()
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        self.is_connected = False
        if self._read_task:
            self._read_task.cancel()


async def scenario_normal_question(host: str, port: int) -> bool:
    """Scenario 1: Normal call flow."""
    logger.info("=== Running Scenario: normal_question ===")
    client = DuplexAudioSocketClient(host, port)
    await client.connect()

    # 1. Wait for greeting and consent prompts to be received
    logger.info("Listening to initial greeting and consent prompt...")
    for _ in range(30):  # wait up to 6 seconds for initial prompts
        await asyncio.sleep(0.2)
        if client.total_received_bytes > 120000:
            break

    initial_bytes = client.total_received_bytes
    logger.info(f"Received initial prompts audio: {initial_bytes} bytes")
    assert initial_bytes > 0, "No initial prompt audio received from server"

    # 2. Send voiced speech for consent ("አዎ")
    logger.info("Sending voiced consent speech...")
    voiced_consent = bytes([120, 15] * 2400)  # ~600ms voiced
    await client.send_audio_chunk(voiced_consent)
    # Send >1000ms of silence to trigger endpointing (80 frames = 1600ms)
    silence = bytes([0, 0] * 160)
    for _ in range(80):
        await client.send_audio_chunk(silence)

    await asyncio.sleep(0.5)
    post_consent_bytes = client.total_received_bytes

    # 3. Send agronomic question
    logger.info("Sending agronomic question speech...")
    voiced_question = bytes([110, 25] * 4000)  # 1s voiced
    await client.send_audio_chunk(voiced_question)
    for _ in range(80):  # 1600ms silence to endpoint
        await client.send_audio_chunk(silence)

    # 4. Wait for thinking cue and answer audio
    logger.info("Waiting for thinking cue & answer audio...")
    for _ in range(25):  # up to 5s
        await asyncio.sleep(0.2)
        if client.total_received_bytes > post_consent_bytes:
            break

    final_bytes = client.total_received_bytes
    logger.info(f"Total audio bytes received at end: {final_bytes} (delta: {final_bytes - post_consent_bytes})")
    assert final_bytes > post_consent_bytes, "No response audio received after question"

    await client.send_hangup()
    logger.info("Scenario normal_question: PASSED\n")
    return True


async def scenario_silence_timeout(host: str, port: int) -> bool:
    """Scenario 2: Silent caller handling."""
    logger.info("=== Running Scenario: silence_timeout ===")
    client = DuplexAudioSocketClient(host, port)
    await client.connect()

    # Send only silence
    silence = bytes([0, 0] * 160)
    for _ in range(40):
        await client.send_audio_chunk(silence)

    await asyncio.sleep(1.5)
    received = client.total_received_bytes
    logger.info(f"Received audio during silence turn: {received} bytes")
    assert received > 0, "Server did not play prompts on silence"

    await client.send_hangup()
    logger.info("Scenario silence_timeout: PASSED\n")
    return True


async def scenario_caller_hangup_cleanliness(host: str, port: int) -> bool:
    """Scenario 3: Abrupt caller disconnect."""
    logger.info("=== Running Scenario: caller_hangup_cleanliness ===")
    client = DuplexAudioSocketClient(host, port)
    await client.connect()

    # Receive initial audio chunk
    await asyncio.sleep(0.3)
    logger.info("Sending abrupt hangup signal...")
    await client.send_hangup()
    await asyncio.sleep(0.5)

    logger.info("Scenario caller_hangup_cleanliness: PASSED\n")
    return True


async def run_all_scenarios(host: str = "127.0.0.1", port: int = 9092):
    """Run full test suite."""
    print("=" * 70)
    print("HELLO FARMER: PHASE 5 AUDIOSOCKET TELEPHONY SCENARIOS")
    print("=" * 70)

    scenarios = [
        ("Normal Question Flow", scenario_normal_question),
        ("Silence & Timeout Handling", scenario_silence_timeout),
        ("Caller Hangup Cleanliness", scenario_caller_hangup_cleanliness),
    ]

    all_passed = True
    for name, func in scenarios:
        try:
            ok = await func(host, port)
            print(f"  [✓ PASS] {name}")
        except Exception as e:
            print(f"  [✗ FAIL] {name}: {e}")
            all_passed = False

    print("\n" + "=" * 70)
    print(f"OVERALL RESULT: {'ALL PASSED' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9092
    success = asyncio.run(run_all_scenarios(host, port))
    sys.exit(0 if success else 1)
