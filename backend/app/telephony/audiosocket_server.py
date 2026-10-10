"""Asterisk AudioSocket TCP Server implementation.

Asterisk app_audiosocket connects to this TCP server streaming 8 kHz 16-bit mono signed linear PCM.
Protocol wire format:
  Header:
    Type: 1 byte (0x01 = Hangup, 0x02 = Audio, 0x03 = Error)
    Payload Length: 2 bytes (Big Endian uint16)
  Initial Connection:
    16-byte UUID identifying the call / channel.
"""
import asyncio
import logging
import struct
import uuid

logger = logging.getLogger("hello_farmer.audiosocket")

# Asterisk res_audiosocket.c protocol constants:
# 0x00 = Hangup / connection termination
# 0x01 = Call UUID (16 bytes payload)
# 0x02 = Silence
# 0x03 = DTMF digit
# 0x10 = 16-bit 8kHz signed linear mono PCM audio
# 0x11 - 0x18 = Higher sample rate SLIN audio
# 0xFF = Error
TYPE_HANGUP = 0x00
TYPE_UUID = 0x01
TYPE_SILENCE = 0x02
TYPE_DTMF = 0x03
TYPE_AUDIO = 0x10
TYPE_ERROR = 0xFF


class AudioSocketConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.call_uuid: str | None = None
        self.is_active = True

    async def initialize(self):
        """Read initial AudioSocket handshake from Asterisk (Type 0x01 + 16 bytes UUID)."""
        try:
            # AudioSocket message header is 3 bytes: 1 byte Type, 2 bytes Length (big endian)
            header = await self.reader.readexactly(3)
            msg_type, length = struct.unpack("!BH", header)
            if msg_type == TYPE_UUID and length == 16:
                uuid_bytes = await self.reader.readexactly(16)
                self.call_uuid = str(uuid.UUID(bytes=uuid_bytes))
            elif length == 16:
                uuid_bytes = await self.reader.readexactly(16)
                self.call_uuid = str(uuid.UUID(bytes=uuid_bytes))
            else:
                # Raw 16-byte fallback if no 3-byte header
                rest = await self.reader.readexactly(13)
                self.call_uuid = str(uuid.UUID(bytes=header + rest))

            logger.info(f"AudioSocket call initialized with UUID: {self.call_uuid}")
            print(f"\n📞 [AUDIOSOCKET 🎧] Call connected! UUID: {self.call_uuid}", flush=True)
        except Exception as e:
            logger.error(f"Failed to read AudioSocket UUID handshake: {e}")
            self.is_active = False

    def drain_audio_buffer(self):
        """Drain buffered frames accumulated in TCP reader during outgoing playback."""
        drained_count = 0
        try:
            while len(self.reader._buffer) >= 3:
                header = self.reader._buffer[:3]
                msg_type, length = struct.unpack("!BH", header)
                frame_len = 3 + length
                if len(self.reader._buffer) < frame_len:
                    break
                del self.reader._buffer[:frame_len]
                drained_count += 1
            if drained_count > 0:
                print(f"🧹 [BUFFER DRAIN] Cleared {drained_count} buffered frames from playback. Listening to caller in real time!", flush=True)
        except Exception as e:
            logger.warning(f"Error draining audio buffer: {e}")


    async def read_frame(self) -> tuple[int, bytes] | None:
        """Read a single AudioSocket protocol frame."""
        try:
            header = await self.reader.readexactly(3)
            msg_type, length = struct.unpack("!BH", header)
            payload = await self.reader.readexactly(length) if length > 0 else b""
            return msg_type, payload
        except (asyncio.IncompleteReadError, ConnectionResetError):
            self.is_active = False
            return None
        except Exception as e:
            logger.error(f"Error reading AudioSocket frame: {e}")
            self.is_active = False
            return None

    async def send_audio(self, pcm_data: bytes, pace: bool = True):
        """Send 8 kHz signed linear mono PCM audio chunk to Asterisk with real-time clock pacing."""
        if not self.is_active or self.writer.is_closing():
            return
        try:
            # Chunk into standard telephony frame (320 bytes = 20ms of 8kHz 16-bit linear PCM)
            chunk_size = 320
            for i in range(0, len(pcm_data), chunk_size):
                if not self.is_active or self.writer.is_closing():
                    break
                chunk = pcm_data[i:i + chunk_size]
                header = struct.pack("!BH", TYPE_AUDIO, len(chunk))
                self.writer.write(header + chunk)
                await self.writer.drain()
                if pace:
                    # 19ms sleep ensures steady 20ms frame delivery matching Asterisk clock
                    await asyncio.sleep(0.019)
        except Exception as e:
            logger.error(f"Error sending audio frame to Asterisk: {e}")
            self.is_active = False

    async def hangup(self):
        """Send clean hangup signal to Asterisk."""
        if self.writer.is_closing():
            return
        try:
            header = struct.pack("!BH", TYPE_HANGUP, 0)
            self.writer.write(header)
            await self.writer.drain()
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass
        finally:
            self.is_active = False


class AudioSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 9092):
        self.host = host
        self.port = port
        self.server: asyncio.Server | None = None
        self.active_calls: dict[str, AudioSocketConnection] = {}

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        conn = AudioSocketConnection(reader, writer)
        await conn.initialize()
        if not conn.is_active or not conn.call_uuid:
            writer.close()
            return

        self.active_calls[conn.call_uuid] = conn
        logger.info(f"New caller connected: {conn.call_uuid}. Total active calls: {len(self.active_calls)}")

        try:
            try:
                from app.telephony.call_flow import CallStateMachine
            except ImportError:
                from backend.app.telephony.call_flow import CallStateMachine
            sm = CallStateMachine(conn)
            await sm.run()
        except Exception as e:
            logger.error(f"Exception in call loop {conn.call_uuid}: {e}")
        finally:
            if conn.call_uuid in self.active_calls:
                del self.active_calls[conn.call_uuid]
            await conn.hangup()
            logger.info(f"Call closed: {conn.call_uuid}. Remaining active calls: {len(self.active_calls)}")

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"AudioSocket TCP server listening on {self.host}:{self.port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("AudioSocket TCP server stopped.")

    def get_status(self) -> dict:
        return {
            "status": "online" if (self.server and self.server.is_serving()) else ("ready" if self.server else "offline"),
            "active_calls_count": len(self.active_calls),
            "active_call_ids": list(self.active_calls.keys()),
            "host": self.host,
            "port": self.port,
        }

