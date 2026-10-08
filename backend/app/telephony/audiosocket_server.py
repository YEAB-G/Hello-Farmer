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

TYPE_HANGUP = 0x01
TYPE_AUDIO = 0x02
TYPE_ERROR = 0x03


class AudioSocketConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.call_uuid: str | None = None
        self.is_active = True

    async def initialize(self):
        """Read initial 16-byte UUID handshake from Asterisk."""
        try:
            uuid_bytes = await self.reader.readexactly(16)
            self.call_uuid = str(uuid.UUID(bytes=uuid_bytes))
            logger.info(f"AudioSocket call initialized with UUID: {self.call_uuid}")
        except Exception as e:
            logger.error(f"Failed to read AudioSocket UUID handshake: {e}")
            self.is_active = False

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

    async def send_audio(self, pcm_data: bytes):
        """Send 8 kHz signed linear mono PCM audio chunk to Asterisk."""
        if not self.is_active or self.writer.is_closing():
            return
        try:
            # Chunk into max payload size (typically 320 bytes = 20ms of 8kHz 16-bit audio)
            chunk_size = 320
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i:i + chunk_size]
                header = struct.pack("!BH", TYPE_AUDIO, len(chunk))
                self.writer.write(header + chunk)
                await self.writer.drain()
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
