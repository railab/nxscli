"""Optional control-server plugin for nxscli."""

import base64
import json
import os
import socket
import threading
from dataclasses import dataclass
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, cast

from nxslib.comm import AckMode
from nxslib.plugin import INxscopePlugin
from nxslib.proto.iparse import ParseAck

if TYPE_CHECKING:
    from nxslib.plugin import INxscopeControl


@dataclass(frozen=True)
class ControlResult:
    """Response from control server client calls."""

    ok: bool
    data: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class _EndpointConfig:
    """Parsed endpoint configuration."""

    family: int
    bind_addr: Any
    connect_addr: Any
    cleanup_path: str | None


def _require_af_unix(endpoint: str) -> None:
    """Fail early for unix endpoints on platforms without AF_UNIX."""
    if not hasattr(socket, "AF_UNIX"):
        raise ValueError(
            f"unix endpoint '{endpoint}' is not supported on this platform; "
            "use tcp://<host>:<port>"
        )


def _parse_endpoint(endpoint: str) -> _EndpointConfig:
    """Parse IPC endpoint string into socket configuration."""
    if endpoint.startswith("tcp://"):
        host_port = endpoint[len("tcp://") :]
        host, port_s = host_port.rsplit(":", 1)
        port = int(port_s, 10)
        addr_tcp = (host, port)
        return _EndpointConfig(
            family=socket.AF_INET,
            bind_addr=addr_tcp,
            connect_addr=addr_tcp,
            cleanup_path=None,
        )

    if endpoint.startswith("unix-abstract://"):
        _require_af_unix(endpoint)
        name = endpoint[len("unix-abstract://") :]
        if not name:
            raise ValueError("unix-abstract endpoint name cannot be empty")
        addr_unix_abstract = "\x00" + name
        return _EndpointConfig(
            family=socket.AF_UNIX,
            bind_addr=addr_unix_abstract,
            connect_addr=addr_unix_abstract,
            cleanup_path=None,
        )

    path = endpoint
    if endpoint.startswith("unix://"):
        _require_af_unix(endpoint)
        path = endpoint[len("unix://") :]
    else:
        _require_af_unix(endpoint)
    if not path:
        raise ValueError("unix endpoint path cannot be empty")
    return _EndpointConfig(
        family=socket.AF_UNIX,
        bind_addr=path,
        connect_addr=path,
        cleanup_path=path,
    )


class ControlServerPlugin(INxscopePlugin):
    """Nxslib plugin exposing control surface via local IPC endpoint."""

    name = "control_server"

    def __init__(self, endpoint: str):
        """Initialize plugin and parse configured control endpoint."""
        self._endpoint = _parse_endpoint(endpoint)
        self._control: "INxscopeControl | None" = None
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def on_register(self, control: "INxscopeControl") -> None:
        """Attach control surface and start IPC server thread."""
        self._control = control
        self._start()

    def on_unregister(self) -> None:
        """Stop IPC server and detach control surface."""
        self._stop_server()
        self._control = None

    def _start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        if self._endpoint.cleanup_path is not None:
            os.makedirs(
                os.path.dirname(self._endpoint.cleanup_path) or ".",
                exist_ok=True,
            )
            try:
                os.unlink(self._endpoint.cleanup_path)
            except FileNotFoundError:
                pass

        self._sock = socket.socket(self._endpoint.family, socket.SOCK_STREAM)
        self._sock.bind(self._endpoint.bind_addr)
        self._sock.listen(4)
        self._sock.settimeout(0.2)
        self._stop.clear()

        self._thread = threading.Thread(
            target=self._serve_loop,
            name="nxscli_control",
            daemon=True,
        )
        self._thread.start()

    def _stop_server(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

        if self._endpoint.cleanup_path is not None:
            try:
                os.unlink(self._endpoint.cleanup_path)
            except FileNotFoundError:
                pass

    def _serve_loop(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break

            with conn:
                conn.settimeout(1.0)
                try:
                    req = self._recv_json(conn)
                    resp = self._handle(req)
                except Exception as exc:
                    resp = {"ok": False, "error": str(exc)}
                self._send_json(conn, resp)

    def _recv_json(self, conn: socket.socket) -> dict[str, Any]:
        buf = bytearray()
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
            if b"\n" in chunk:
                break
        if not buf:
            raise RuntimeError("empty request")
        line = bytes(buf).split(b"\n", 1)[0]
        obj = json.loads(line.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("request must be a JSON object")
        return cast("dict[str, Any]", obj)

    def _send_json(self, conn: socket.socket, resp: dict[str, Any]) -> None:
        payload = json.dumps(resp, separators=(",", ":")).encode("utf-8")
        conn.sendall(payload + b"\n")

    def _handle(self, req: dict[str, Any]) -> dict[str, Any]:
        if self._control is None:
            raise RuntimeError("control server not attached")

        method = req.get("method")
        params = req.get("params", {})

        if method == "send_user_frame":
            payload = base64.b64decode(params["payload_b64"])
            ack = self._control.send_user_frame(
                int(params["fid"]),
                payload,
                ack_mode=AckMode(
                    str(params.get("ack_mode", "disabled")).lower()
                ),
                ack_timeout=float(params.get("ack_timeout", 1.0)),
            )
            return {
                "ok": True,
                "data": {
                    "state": bool(ack.state),
                    "retcode": int(ack.retcode),
                },
            }

        if method == "ext_notify":
            payload = base64.b64decode(params["payload_b64"])
            ack = self._control.ext_notify(
                ext_id=int(params["ext_id"]),
                cmd_id=int(params["cmd_id"]),
                payload=payload,
                fid=int(params.get("fid", 8)),
                ack_mode=AckMode(
                    str(params.get("ack_mode", "disabled")).lower()
                ),
                ack_timeout=float(params.get("ack_timeout", 1.0)),
            )
            return {
                "ok": True,
                "data": {
                    "state": bool(ack.state),
                    "retcode": int(ack.retcode),
                },
            }

        if method == "ext_request":
            payload = base64.b64decode(params["payload_b64"])
            resp = self._control.ext_request(
                ext_id=int(params["ext_id"]),
                cmd_id=int(params["cmd_id"]),
                payload=payload,
                fid=int(params.get("fid", 8)),
                timeout=float(params.get("timeout", 1.0)),
                ack_mode=AckMode(
                    str(params.get("ack_mode", "disabled")).lower()
                ),
                ack_timeout=float(params.get("ack_timeout", 1.0)),
            )
            return {
                "ok": True,
                "data": {
                    "ext_id": int(resp.ext_id),
                    "cmd_id": int(resp.cmd_id),
                    "req_id": int(resp.req_id),
                    "status": int(resp.status),
                    "fid": int(resp.fid),
                    "is_error": bool(resp.is_error),
                    "payload_b64": base64.b64encode(resp.payload).decode(
                        "ascii"
                    ),
                },
            }

        raise ValueError(f"unknown method: {method}")


class ControlClient:
    """Client for nxscli ControlServerPlugin endpoint."""

    def __init__(self, endpoint: str, timeout: float = 1.0):
        """Initialize control client bound to given endpoint."""
        self._endpoint = _parse_endpoint(endpoint)
        self._timeout = timeout
        self._last_error: str | None = None

    @property
    def last_error(self) -> str | None:
        """Return last control client error string."""
        return self._last_error

    def _call(self, method: str, params: dict[str, Any]) -> ControlResult:
        self._last_error = None
        try:
            with socket.socket(
                self._endpoint.family, socket.SOCK_STREAM
            ) as sock:
                sock.settimeout(self._timeout)
                sock.connect(self._endpoint.connect_addr)

                req = {"method": method, "params": params}
                wire = json.dumps(req, separators=(",", ":")).encode("utf-8")
                sock.sendall(wire + b"\n")

                buf = bytearray()
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buf.extend(chunk)
                    if b"\n" in chunk:
                        break
                if not buf:
                    self._last_error = "empty response"
                    return ControlResult(False, {}, self._last_error)

                line = bytes(buf).split(b"\n", 1)[0]
                obj = json.loads(line.decode("utf-8"))
                return ControlResult(
                    ok=bool(obj.get("ok", False)),
                    data=dict(obj.get("data", {})),
                    error=obj.get("error"),
                )
        except (OSError, ValueError, JSONDecodeError) as exc:
            self._last_error = str(exc)
            return ControlResult(False, {}, self._last_error)

    def send_user_frame(
        self,
        fid: int,
        payload: bytes,
        ack_mode: str = "disabled",
        ack_timeout: float = 1.0,
    ) -> ParseAck:
        """Proxy send_user_frame."""
        ret = self._call(
            "send_user_frame",
            {
                "fid": int(fid),
                "payload_b64": base64.b64encode(payload).decode("ascii"),
                "ack_mode": ack_mode,
                "ack_timeout": float(ack_timeout),
            },
        )
        if not ret.ok:
            return ParseAck(False, -1)
        return ParseAck(
            bool(ret.data.get("state", False)),
            int(ret.data.get("retcode", -1)),
        )

    def ext_notify(
        self,
        ext_id: int,
        cmd_id: int,
        payload: bytes,
        fid: int = 8,
        ack_mode: str = "disabled",
        ack_timeout: float = 1.0,
    ) -> ParseAck:
        """Proxy ext_notify."""
        ret = self._call(
            "ext_notify",
            {
                "ext_id": int(ext_id),
                "cmd_id": int(cmd_id),
                "payload_b64": base64.b64encode(payload).decode("ascii"),
                "fid": int(fid),
                "ack_mode": ack_mode,
                "ack_timeout": float(ack_timeout),
            },
        )
        if not ret.ok:
            return ParseAck(False, -1)
        return ParseAck(
            bool(ret.data.get("state", False)),
            int(ret.data.get("retcode", -1)),
        )

    def ext_request(
        self,
        ext_id: int,
        cmd_id: int,
        payload: bytes,
        fid: int = 8,
        timeout: float = 1.0,
        ack_mode: str = "disabled",
        ack_timeout: float = 1.0,
    ) -> ControlResult:
        """Proxy ext_request."""
        return self._call(
            "ext_request",
            {
                "ext_id": int(ext_id),
                "cmd_id": int(cmd_id),
                "payload_b64": base64.b64encode(payload).decode("ascii"),
                "fid": int(fid),
                "timeout": float(timeout),
                "ack_mode": ack_mode,
                "ack_timeout": float(ack_timeout),
            },
        )
