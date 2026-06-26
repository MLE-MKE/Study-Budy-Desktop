"""Lifecycle wrapper for the private Study Budy overlay server."""

from __future__ import annotations

import socket
import threading
from dataclasses import dataclass

from werkzeug.serving import BaseWSGIServer, make_server

from .overlay_service import create_overlay_app
from .storage import TaskRepository


class OverlayServerError(RuntimeError):
    """A local overlay server could not be started."""


@dataclass
class OverlayServer:
    repository: TaskRepository
    host: str = "127.0.0.1"
    port: int = 5155
    _server: BaseWSGIServer | None = None
    _thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/overlay"

    @property
    def checkin_url(self) -> str:
        return f"http://{self.host}:{self.port}/checkin"

    @property
    def timer_url(self) -> str:
        return f"http://{self.host}:{self.port}/timer"

    def start(self) -> None:
        if self.running:
            return
        if not is_port_available(self.host, self.port):
            raise OverlayServerError(
                f"Port {self.port} is unavailable. Choose a different overlay port in Settings."
            )
        try:
            server = make_server(self.host, self.port, create_overlay_app(self.repository), threaded=True)
        except OSError as exc:
            if exc.errno in {48, 98, 10013, 10048}:
                raise OverlayServerError(
                    f"Port {self.port} is unavailable. Choose a different overlay port in Settings."
                ) from exc
            raise OverlayServerError(f"The local overlay service could not start: {exc}") from exc
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="study-budy-overlay", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None

    def restart(self) -> None:
        self.stop()
        self.start()


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex((host, port)) != 0


def choose_available_port(host: str, preferred_port: int = 5155) -> int:
    """Use a memorable default while recovering gracefully from port conflicts."""
    for port in range(preferred_port, preferred_port + 100):
        if is_port_available(host, port):
            return port
    raise OverlayServerError("No available port was found for the local overlay service.")
