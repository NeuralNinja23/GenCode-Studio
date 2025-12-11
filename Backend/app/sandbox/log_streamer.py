"""
Log Streamer
Real-time streaming of Docker container logs via WebSocket

This implementation uses the `docker` CLI instead of the Python docker SDK.
"""

import asyncio
from typing import Dict, Any, Optional, Callable


class LogStreamer:
    """
    Streams container logs in real-time using `docker logs -f`.
    """

    def __init__(self, docker_client: Optional[Any] = None):
        # docker_client is kept only for backwards compatibility; it's unused.
        self.docker_client = docker_client
        self.stream_processes: Dict[str, asyncio.subprocess.Process] = {}

    async def _stream_logs_from_cli(
        self,
        stream_id: str,
        container_id: str,
        websocket_send: Callable[[str], Any],
    ) -> None:
        """
        Internal helper: run `docker logs -f` on the container and forward
        each line to `websocket_send(line)`.
        
        NOTE: On Windows, asyncio.create_subprocess_exec doesn't work with SelectorEventLoop.
        We use a hybrid approach: run blocking in thread, then stream.
        """
        import subprocess
        print(f"[LOG_STREAM] Starting docker logs for container {container_id} (stream_id={stream_id})")

        try:
            # Use Popen for streaming (can't use subprocess.run for continuous output)
            # Run in a way that's compatible with Windows
            def start_process():
                return subprocess.Popen(
                    ["docker", "logs", "-f", container_id],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,  # Line buffered
                )
            
            process = await asyncio.to_thread(start_process)
            self.stream_processes[stream_id] = process  # Store for stop_streaming

            while True:
                # Read line in thread to avoid blocking
                line = await asyncio.to_thread(process.stdout.readline)
                if not line:
                    break  # process exited

                text = line.rstrip("\n")
                if not text:
                    continue

                # We send the raw text line to the callback
                await websocket_send(text)
        except asyncio.CancelledError:
            print(f"[LOG_STREAM] Log streaming cancelled for {stream_id}")
        except Exception as e:
            print(f"[LOG_STREAM] Error while streaming logs for {stream_id}: {e}")
        finally:
            self.stream_processes.pop(stream_id, None)
            if 'process' in dir() and process and process.poll() is None:
                process.terminate()
            print(f"[LOG_STREAM] Log streaming ended for {stream_id}")

    async def start_streaming(
        self,
        stream_id: str,
        container_id: str,
        websocket_send: Callable[[str], Any],
    ) -> None:
        """
        Start streaming logs for a container.

        `websocket_send` is an async function that takes a string log line.
        """
        # Run the streaming task in the background
        asyncio.create_task(
            self._stream_logs_from_cli(stream_id, container_id, websocket_send)
        )
        print(f"[LOG_STREAM] Started streaming {stream_id}")

    async def stop_streaming(self, stream_id: str) -> None:
        """
        Stop a log stream, if running.
        """
        process = self.stream_processes.get(stream_id)
        if process and process.returncode is None:
            print(f"[LOG_STREAM] Terminating log stream process for {stream_id}")
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
        self.stream_processes.pop(stream_id, None)
        print(f"[LOG_STREAM] Stopped streaming {stream_id}")

    async def stop_all_streams(self) -> None:
        """
        Stop all active log streams.
        """
        for stream_id in list(self.stream_processes.keys()):
            await self.stop_streaming(stream_id)
