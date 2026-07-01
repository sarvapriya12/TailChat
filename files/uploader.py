import asyncio
import os
import json
import time
from network.protocol import send_packet
from utils.logger import logger

async def stream_file_to_host(host_ip: str, file_port: int, file_id: str, file_path: str, progress_callback=None) -> bool:
    """
    Streams a local file to the Host's forwarding server over TCP.
    Updates progress_callback(bytes_sent, total_bytes).
    """
    if not os.path.exists(file_path):
        logger.error(f"Upload failed: File does not exist: {file_path}")
        return False
        
    total_size = os.path.getsize(file_path)
    logger.info(f"Starting file stream for {file_path} ({total_size} bytes)")
    
    reader, writer = None, None
    try:
        # 1. Connect to host file server
        reader, writer = await asyncio.open_connection(host_ip, file_port)
        
        # 2. Send header packet identifying this connection as the sender
        header = {
            "file_id": file_id,
            "role": "sender"
        }
        await send_packet(writer, header)
        
        # =====================================================================
        # OLD FIXED STRATEGY (COMMENTED OUT FOR REFERENCE)
        # =====================================================================
        # What it did: It read and sent files in rigid 64KB blocks.
        # Why we are not using it: On fast networks (like direct Tailscale peer
        # connections), transferring in 64KB chunks creates high CPU overhead
        # because of the frequent python asyncio event-loop wakeups and progress
        # triggers. On slow connections, 64KB can block the write buffer too long.
        # 
        # bytes_sent = 0
        # chunk_size = 64 * 1024  # 64KB
        # with open(file_path, "rb") as f:
        #     while True:
        #         chunk = f.read(chunk_size)
        #         if not chunk:
        #             break
        #         writer.write(chunk)
        #         await writer.drain()
        #         bytes_sent += len(chunk)
        #         if progress_callback:
        #             progress_callback(bytes_sent, total_size)
        # =====================================================================

        # NEW ADAPTIVE CHUNKING STRATEGY (Jitter & Speed-Aware)
        # Automatically scales chunk size based on network latency/drain speed.
        bytes_sent = 0
        current_chunk_size = 32 * 1024  # Start at 32KB
        min_chunk = 16 * 1024           # 16KB minimum
        max_chunk = 1024 * 1024         # 1MB maximum
        
        with open(file_path, "rb") as f:
            while True:
                # Read dynamic chunk size
                chunk = f.read(current_chunk_size)
                if not chunk:
                    break
                
                # Measure how long the socket takes to drain
                start_time = time.perf_counter()
                writer.write(chunk)
                await writer.drain()
                elapsed = time.perf_counter() - start_time
                
                bytes_sent += len(chunk)
                if progress_callback:
                    progress_callback(bytes_sent, total_size)
                
                # Adaptive Adjustment:
                # - If the socket drains extremely fast (< 5ms), double the chunk size
                #   to reduce Python CPU overhead and maximize throughput.
                # - If the socket takes too long (> 50ms), halve the chunk size
                #   to maintain high-frequency progress updates and prevent stalls.
                if elapsed < 0.005:
                    current_chunk_size = min(current_chunk_size * 2, max_chunk)
                elif elapsed > 0.050:
                    current_chunk_size = max(current_chunk_size // 2, min_chunk)
                    
        logger.info(f"Successfully finished streaming file {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error during file upload streaming: {e}")
        return False
    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception: pass
