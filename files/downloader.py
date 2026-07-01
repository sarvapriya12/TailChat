import asyncio
import json
from network.protocol import send_packet
from utils.logger import logger

async def stream_file_from_host(host_ip: str, file_port: int, file_id: str, save_path: str, total_size: int, progress_callback=None) -> bool:
    """
    Downloads a stream of bytes from the Host's forwarding server over TCP and writes it to save_path.
    Updates progress_callback(bytes_received, total_bytes).
    """
    logger.info(f"Starting download stream for File {file_id} to {save_path}")
    
    reader, writer = None, None
    try:
        # 1. Connect to host file server
        reader, writer = await asyncio.open_connection(host_ip, file_port)
        
        # 2. Send header packet identifying this connection as the recipient
        header = {
            "file_id": file_id,
            "role": "recipient"
        }
        await send_packet(writer, header)
        
        # 3. Read chunks from stream and write to disk
        bytes_received = 0
        chunk_size = 64 * 1024  # 64KB
        
        with open(save_path, "wb") as f:
            while bytes_received < total_size:
                # Read from socket
                chunk = await reader.read(chunk_size)
                if not chunk:
                    break
                    
                # Write to disk
                f.write(chunk)
                bytes_received += len(chunk)
                
                if progress_callback:
                    progress_callback(bytes_received, total_size)
                    
        if bytes_received < total_size:
            logger.warning(f"Download ended prematurely: received {bytes_received}/{total_size} bytes.")
            return False
            
        logger.info(f"Successfully finished downloading file {file_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error during file download streaming: {e}")
        return False
    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception: pass
