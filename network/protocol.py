import json
import asyncio
from utils.logger import logger

# Maximum allowed packet size (1MB) to prevent denial-of-service via memory exhaustion
MAX_PACKET_SIZE = 1_048_576

async def send_packet(writer: asyncio.StreamWriter, packet: dict) -> bool:
    """Serializes a packet to JSON, appends a newline, and writes to stream."""
    try:
        data = json.dumps(packet) + "\n"
        writer.write(data.encode("utf-8"))
        await writer.drain()
        return True
    except Exception as e:
        logger.debug(f"Failed to send packet: {e}")
        return False

async def read_packet(reader: asyncio.StreamReader) -> dict | None:
    """Reads a newline-terminated line from the stream and parses it as JSON.
    Enforces a maximum packet size to prevent memory exhaustion attacks."""
    try:
        line = await reader.readuntil(b'\n')
        if not line:
            return None
        if len(line) > MAX_PACKET_SIZE:
            logger.warning(f"Dropped oversized packet: {len(line)} bytes (max {MAX_PACKET_SIZE})")
            return None
        return json.loads(line.decode("utf-8").strip())
    except asyncio.IncompleteReadError:
        return None
    except asyncio.LimitOverrunError:
        logger.warning("Packet exceeded stream buffer limit. Dropping connection.")
        return None
    except Exception as e:
        logger.debug(f"Failed to read/parse packet: {e}")
        return None

