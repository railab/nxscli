import base64
import socket
from dataclasses import dataclass
from pathlib import Path

import pytest  # type: ignore
from nxslib.proto.iparse import ParseAck

from nxscli.control_server import (
    ControlClient,
    ControlServerPlugin,
    _parse_endpoint,
)
from tests.fake_nxscope import FakeNxscope


def _get_test_endpoint(name: str) -> str:
    if hasattr(socket, "AF_UNIX"):
        return f"unix-abstract://{name}"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
    return f"tcp://{host}:{port}"


def _ensure_af_unix(monkeypatch: pytest.MonkeyPatch) -> None:
    desired = getattr(socket, "AF_UNIX", 1)
    monkeypatch.setattr(socket, "AF_UNIX", desired, raising=False)


class _DummySocket:
    def __init__(self, family, sock_type):
        self.family = family
        self.sock_type = sock_type
        self.closed = False

    def bind(self, addr):
        self.addr = addr

    def listen(self, backlog):
        self.backlog = backlog

    def settimeout(self, timeout):
        self.timeout = timeout

    def close(self):
        self.closed = True


class _DummyThread:
    def __init__(self, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True

    def is_alive(self):
        return False

    def join(self, timeout=None):
        del timeout


class _SockCloseErr(_DummySocket):
    def close(self):
        raise OSError("close failed")


def _patch_control_server_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("nxscli.control_server.socket.socket", _DummySocket)
    monkeypatch.setattr("nxscli.control_server.threading.Thread", _DummyThread)
    monkeypatch.setattr(
        "nxscli.control_server.ControlServerPlugin._serve_loop",
        lambda self: None,
        raising=False,
    )


@dataclass(frozen=True)
class _Resp:
    ext_id: int
    cmd_id: int
    req_id: int
    status: int
    payload: bytes
    fid: int
    is_error: bool


class _ControlStub:
    def __init__(self):
        self.calls = []

    def send_user_frame(self, fid, payload, ack_mode="auto", ack_timeout=1.0):
        self.calls.append(("send", int(fid), payload, ack_mode, ack_timeout))
        return ParseAck(True, 11)

    def ext_notify(
        self,
        ext_id,
        cmd_id,
        payload,
        fid=8,
        ack_mode="auto",
        ack_timeout=1.0,
    ):
        self.calls.append(
            (
                "notify",
                int(ext_id),
                int(cmd_id),
                payload,
                int(fid),
                ack_mode,
                ack_timeout,
            )
        )
        return ParseAck(True, 22)

    def ext_request(
        self,
        ext_id,
        cmd_id,
        payload,
        fid=8,
        timeout=1.0,
        ack_mode="auto",
        ack_timeout=1.0,
    ):
        self.calls.append(
            (
                "request",
                int(ext_id),
                int(cmd_id),
                payload,
                int(fid),
                timeout,
                ack_mode,
                ack_timeout,
            )
        )
        return _Resp(
            ext_id=int(ext_id),
            cmd_id=int(cmd_id),
            req_id=31,
            status=0,
            payload=b"ok",
            fid=int(fid),
            is_error=False,
        )


def test_control_server_roundtrip_unix_abstract():
    endpoint = _get_test_endpoint("nxscli-test-control")
    plugin = ControlServerPlugin(endpoint)
    control = _ControlStub()

    plugin.on_register(control)
    try:
        client = ControlClient(endpoint, timeout=0.5)

        ack = client.send_user_frame(8, b"\x01", ack_mode="disabled")
        assert ack.state is True
        assert ack.retcode == 11

        ack = client.ext_notify(0x21, 2, b"abc")
        assert ack.state is True
        assert ack.retcode == 22

        ret = client.ext_request(0x21, 1, b"xyz", timeout=0.2)
        assert ret.ok is True
        assert ret.data["ext_id"] == 0x21
        assert ret.data["cmd_id"] == 1
        assert ret.data["req_id"] == 31
        assert base64.b64decode(ret.data["payload_b64"]) == b"ok"
    finally:
        plugin.on_unregister()


def test_control_server_parse_endpoint_tcp():
    ep = _parse_endpoint("tcp://127.0.0.1:55000")
    assert ep.connect_addr == ("127.0.0.1", 55000)


def test_control_client_connection_error_returns_failed_ack(
    monkeypatch,
):  # type: ignore
    class _DummySock:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def settimeout(self, timeout):
            del timeout

        def connect(self, addr):
            del addr
            raise ConnectionRefusedError(111, "Connection refused")

    monkeypatch.setattr("socket.socket", lambda *a, **k: _DummySock())

    client = ControlClient("tcp://127.0.0.1:55001", timeout=0.1)
    ack = client.send_user_frame(8, b"\x01")
    assert ack.state is False
    assert ack.retcode == -1


def test_control_server_parse_unix_and_invalid_endpoints(monkeypatch):
    _ensure_af_unix(monkeypatch)

    ep = _parse_endpoint("unix-abstract://nxscli.sock")
    assert ep.cleanup_path is None
    assert ep.bind_addr == "\x00nxscli.sock"

    ep = _parse_endpoint("unix:///tmp/nxscli.sock")
    assert ep.cleanup_path == "/tmp/nxscli.sock"
    assert ep.bind_addr == "/tmp/nxscli.sock"

    ep = _parse_endpoint("/tmp/nxscli2.sock")
    assert ep.cleanup_path == "/tmp/nxscli2.sock"
    assert ep.connect_addr == "/tmp/nxscli2.sock"

    with pytest.raises(ValueError):
        _parse_endpoint("unix://")
    with pytest.raises(ValueError):
        _parse_endpoint("unix-abstract://")


def test_control_server_parse_unix_endpoints_without_af_unix(monkeypatch):
    monkeypatch.delattr(socket, "AF_UNIX", raising=False)
    with pytest.raises(ValueError, match="not supported"):
        _parse_endpoint("unix:///tmp/nxscli.sock")
    with pytest.raises(ValueError, match="not supported"):
        _parse_endpoint("unix-abstract://nxscli")
    with pytest.raises(ValueError, match="not supported"):
        _parse_endpoint("/tmp/nxscli2.sock")


def test_control_server_enabled_parse_requires_af_unix(monkeypatch):
    monkeypatch.delattr(socket, "AF_UNIX", raising=False)
    with pytest.raises(ValueError, match="not supported"):
        _parse_endpoint("unix:///tmp/nxscli.sock")
    with pytest.raises(ValueError, match="not supported"):
        _parse_endpoint("unix-abstract://nxscli")
    with pytest.raises(ValueError, match="not supported"):
        _parse_endpoint("/tmp/nxscli2.sock")


def test_control_server_enabled_endpoint_tcp(monkeypatch):
    monkeypatch.delattr(socket, "AF_UNIX", raising=False)
    endpoint = _get_test_endpoint("nxscli-test-endpoint")
    assert endpoint.startswith("tcp://")


def test_control_server_enabled_endpoint_unix(monkeypatch):
    _ensure_af_unix(monkeypatch)
    endpoint = _get_test_endpoint("nxscli-test-endpoint")
    assert endpoint == "unix-abstract://nxscli-test-endpoint"


def test_control_server_handle_validation_paths():
    plugin = ControlServerPlugin(_get_test_endpoint("nxscli-test-handle"))

    with pytest.raises(RuntimeError):
        plugin._handle({"method": "send_user_frame", "params": {}})

    plugin._control = _ControlStub()
    with pytest.raises(ValueError):
        plugin._handle({"method": "unknown", "params": {}})


def test_control_server_start_noop_when_thread_alive():
    plugin = ControlServerPlugin(_get_test_endpoint("nxscli-start-alive"))

    class _AliveThread:
        def is_alive(self):
            return True

    plugin._thread = _AliveThread()
    plugin._start()
    assert isinstance(plugin._thread, _AliveThread)


def test_control_server_recv_json_paths():
    plugin = ControlServerPlugin(_get_test_endpoint("nxscli-test-recv"))

    class _Conn:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        def recv(self, size):
            del size
            if not self._chunks:
                return b""
            return self._chunks.pop(0)

    conn_ok = _Conn([b'{"a":1', b',"b":2}\n'])
    req = plugin._recv_json(conn_ok)
    assert req["a"] == 1
    assert req["b"] == 2
    assert conn_ok.recv(1) == b""

    with pytest.raises(RuntimeError):
        plugin._recv_json(_Conn([b""]))

    with pytest.raises(ValueError):
        plugin._recv_json(_Conn([b"[]\n"]))


def test_control_server_serve_loop_timeout_and_exception_paths():
    plugin = ControlServerPlugin(_get_test_endpoint("nxscli-test-loop"))
    plugin._control = _ControlStub()

    class _ConnOK:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def settimeout(self, timeout):
            del timeout

    class _Sock:
        def __init__(self):
            self.calls = 0

        def accept(self):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError
            if self.calls == 2:
                return (_ConnOK(), None)
            raise OSError("stop")

    sent = []

    def _recv_json(_):
        raise RuntimeError("bad request")

    def _send_json(_, resp):
        sent.append(resp)

    plugin._recv_json = _recv_json
    plugin._send_json = _send_json
    plugin._sock = _Sock()
    plugin._serve_loop()
    assert sent
    assert sent[0]["ok"] is False


def test_control_server_serve_loop_timeout_to_exit_branch():
    plugin = ControlServerPlugin(_get_test_endpoint("nxscli-test-loop-exit"))
    plugin._control = _ControlStub()

    class _Sock:
        def accept(self):
            plugin._stop.set()
            raise TimeoutError

    plugin._sock = _Sock()
    plugin._serve_loop()


def test_control_server_start_stop_unix_cleanup_and_sock_close_error(
    tmp_path, monkeypatch
):
    _ensure_af_unix(monkeypatch)
    _patch_control_server_start(monkeypatch)

    sock_path = Path(tmp_path) / "ctrl.sock"
    plugin = ControlServerPlugin(f"unix://{sock_path}")
    plugin._control = _ControlStub()

    plugin._start()
    try:
        assert plugin._thread is not None
        plugin._start()
    finally:
        plugin._stop_server()

    plugin._stop_server()

    plugin._sock = _SockCloseErr(socket.AF_UNIX, socket.SOCK_STREAM)
    plugin._stop_server()


def test_control_client_response_edge_paths(monkeypatch):  # type: ignore
    class _DummySock:
        def __init__(self, chunks):
            self._chunks = list(chunks)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def settimeout(self, timeout):
            del timeout

        def connect(self, addr):
            del addr

        def sendall(self, data):
            del data

        def recv(self, size):
            del size
            if not self._chunks:
                return b""
            return self._chunks.pop(0)

    assert _DummySock([]).recv(1) == b""

    sock1 = _DummySock([b""])
    monkeypatch.setattr("socket.socket", lambda *a, **k: sock1)
    client = ControlClient("tcp://127.0.0.1:55002", timeout=0.1)
    ret = client.ext_request(1, 2, b"x")
    assert ret.ok is False
    assert client.last_error == "empty response"

    sock2 = _DummySock([b'{"ok":false', b',"error":"x"}', b""])
    monkeypatch.setattr("socket.socket", lambda *a, **k: sock2)
    ack = client.ext_notify(1, 2, b"x")
    assert ack.state is False
    assert ack.retcode == -1

    sock3 = _DummySock([b"not-json\n"])
    monkeypatch.setattr("socket.socket", lambda *a, **k: sock3)
    ack = client.send_user_frame(8, b"a")
    assert ack.state is False
    assert ack.retcode == -1
    assert client.last_error is not None


def test_fake_nxscope_unregister_missing_returns_false():
    nxscope = FakeNxscope()
    assert nxscope.unregister_plugin("missing") is False
