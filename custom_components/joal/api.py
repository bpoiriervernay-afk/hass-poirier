"""Client STOMP minimal (sur WebSocket) pour l'interface web de JOAL."""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import json
import logging
from typing import Any
import uuid

import aiohttp
from yarl import URL

from homeassistant.const import CONF_PORT, CONF_URL
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_PATH_PREFIX, CONF_SECRET_TOKEN

_LOGGER = logging.getLogger(__name__)

APP_PREFIX = "/joal"
TOPICS = ("/global", "/announce", "/config", "/torrents", "/speed")
CONFIG_KEYS = (
    "minUploadRate",
    "maxUploadRate",
    "simultaneousSeed",
    "client",
    "keepTorrentWithZeroLeechers",
    "uploadRatioTarget",
)
RECONNECT_DELAY = 15


class JoalError(HomeAssistantError):
    """Erreur de communication avec JOAL."""


class JoalAuthError(JoalError):
    """JOAL a refusé la connexion (jeton invalide)."""


@dataclass
class JoalState:
    """État de JOAL reconstruit à partir des messages reçus."""

    connected: bool = False
    seeding: bool = False
    active_client: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    clients: list[str] = field(default_factory=list)
    torrents: dict[str, str] = field(default_factory=dict)  # infoHash -> nom
    speeds: dict[str, float] = field(default_factory=dict)  # infoHash -> octets/s

    @property
    def upload_speed(self) -> float:
        return sum(self.speeds.values())


def _frame(command: str, headers: dict[str, str], body: str = "") -> str:
    head = "\n".join([command, *(f"{k}:{v}" for k, v in headers.items())])
    return f"{head}\n\n{body}\x00"


def _parse(raw: str) -> tuple[str, dict[str, str], str] | None:
    raw = raw.lstrip("\r\n")
    if not raw:  # battement de cœur ou fin de trame
        return None
    head, _, body = raw.partition("\n\n")
    command, *lines = head.splitlines()
    headers: dict[str, str] = {}
    for line in lines:
        key, _, value = line.partition(":")
        headers.setdefault(key, value)
    return command, headers, body


def _first(payload: Any, *keys: str) -> Any:
    """Tolère quelques variantes de format de payload."""
    if not isinstance(payload, dict):
        return payload
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def normalize_url(value: str) -> str:
    """Accepte « 192.168.1.10 », « http://joal.lan » ou « https://joal.exemple.fr/ »."""
    value = value.strip()
    url = URL(value if "://" in value else f"http://{value}")
    if url.scheme not in ("http", "https") or not url.host:
        raise ValueError(value)
    return f"{url.scheme}://{url.raw_host}"


class JoalClient:
    """Connexion persistante à JOAL."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        port: int,
        path_prefix: str,
        token: str,
    ) -> None:
        url = URL(normalize_url(base_url))
        secure = url.scheme == "https"
        path = f"/{path_prefix.strip('/')}"
        self._session = session
        self._host = url.host
        self._token = token
        self._url = str(
            URL.build(scheme="wss" if secure else "ws", host=url.host, port=port, path=path)
        )
        self.ui_url = str(
            URL.build(scheme=url.scheme, host=url.host, port=port, path=f"{path}/ui/")
        )
        self.state = JoalState()
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._listeners: list[Callable[[], None]] = []
        self._ready = asyncio.Event()
        self._closing = False

    @classmethod
    def from_data(cls, session: aiohttp.ClientSession, data: Mapping[str, Any]) -> JoalClient:
        return cls(
            session,
            data[CONF_URL],
            data[CONF_PORT],
            data[CONF_PATH_PREFIX],
            data[CONF_SECRET_TOKEN],
        )

    # --- Abonnement des entités -------------------------------------------

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _set_connected(self, value: bool) -> None:
        if self.state.connected != value:
            self.state.connected = value
            self._notify()

    # --- Connexion -----------------------------------------------------------

    async def connect(self) -> None:
        """Ouvre le WebSocket, s'authentifie et s'abonne aux topics."""
        try:
            async with asyncio.timeout(10):
                self._ws = await self._session.ws_connect(self._url, heartbeat=30)
                await self._ws.send_str(
                    _frame(
                        "CONNECT",
                        {
                            "accept-version": "1.2,1.1",
                            "host": self._host,
                            "heart-beat": "0,0",
                            "X-Joal-Username": str(uuid.uuid4()),
                            "X-Joal-Auth-Token": self._token,
                        },
                    )
                )
                msg = await self._ws.receive()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise JoalError(f"connexion impossible à {self._url} : {err}") from err

        frame = None
        if msg.type == aiohttp.WSMsgType.TEXT:
            frame = _parse(msg.data.split("\x00")[0])
        if frame is None or frame[0] != "CONNECTED":
            await self._ws.close()
            if frame and frame[0] == "ERROR":
                raise JoalAuthError(frame[1].get("message", "connexion refusée"))
            raise JoalError(f"réponse inattendue de JOAL : {msg.type} {msg.data!r}")

        # L'état complet est renvoyé par /initialize-me : on repart de zéro
        self.state.torrents.clear()
        self.state.speeds.clear()
        await self._ws.send_str(
            _frame("SUBSCRIBE", {"id": "init", "destination": f"{APP_PREFIX}/initialize-me"})
        )
        for i, topic in enumerate(TOPICS):
            await self._ws.send_str(_frame("SUBSCRIBE", {"id": f"sub-{i}", "destination": topic}))
        self._set_connected(True)

    async def wait_ready(self, timeout: float) -> bool:
        """Attend la réception de la configuration initiale."""
        try:
            async with asyncio.timeout(timeout):
                await self._ready.wait()
        except TimeoutError:
            return False
        return True

    async def run(self) -> None:
        """Boucle de lecture avec reconnexion automatique."""
        while not self._closing:
            try:
                if self._ws is None or self._ws.closed:
                    await self.connect()
                await self._read_loop()
            except JoalError as err:
                _LOGGER.warning("JOAL injoignable : %s", err)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Erreur inattendue dans le client JOAL")
            self._set_connected(False)
            if not self._closing:
                await asyncio.sleep(RECONNECT_DELAY)

    async def close(self) -> None:
        self._closing = True
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()

    # --- Réception ---------------------------------------------------------

    async def _read_loop(self) -> None:
        assert self._ws is not None
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                for chunk in msg.data.split("\x00"):
                    self._handle(chunk)

    def _handle(self, chunk: str) -> None:
        frame = _parse(chunk)
        if frame is None:
            return
        command, headers, body = frame
        if command == "ERROR":
            _LOGGER.error("Erreur renvoyée par JOAL : %s %s", headers.get("message"), body)
            return
        if command != "MESSAGE":
            return
        try:
            data = json.loads(body)
        except ValueError:
            _LOGGER.debug("Message non JSON ignoré : %s", body)
            return
        for message in data if isinstance(data, list) else [data]:
            if isinstance(message, dict):
                self._apply(message)
        self._notify()

    def _apply(self, message: dict[str, Any]) -> None:
        mtype = message.get("type")
        payload = message.get("payload") or {}
        _LOGGER.debug("JOAL %s : %s", mtype, payload)
        state = self.state

        if mtype == "GLOBAL_SEED_STARTED":
            state.seeding = True
            client = _first(payload, "client", "clientName")
            if isinstance(client, dict):
                client = client.get("name") or client.get("userAgent")
            state.active_client = client
        elif mtype == "GLOBAL_SEED_STOPPED":
            state.seeding = False
            state.active_client = None
            state.speeds.clear()
        elif mtype == "CONFIG_HAS_BEEN_LOADED":
            config = _first(payload, "config")
            state.config = dict(config if isinstance(config, dict) else payload)
            self._ready.set()
        elif mtype == "LIST_OF_CLIENT_FILES":
            state.clients = sorted(str(c) for c in (_first(payload, "clients") or []))
        elif mtype == "TORRENT_FILE_ADDED":
            if info_hash := payload.get("infoHash"):
                state.torrents[info_hash] = payload.get("name", info_hash)
        elif mtype == "TORRENT_FILE_DELETED":
            info_hash = payload.get("infoHash")
            state.torrents.pop(info_hash, None)
            state.speeds.pop(info_hash, None)
        elif mtype == "SEEDING_SPEED_HAS_CHANGED":
            for item in _first(payload, "speeds") or []:
                if isinstance(item, dict) and (info_hash := item.get("infoHash")):
                    state.speeds[info_hash] = float(
                        item.get("bytesPerSecond", item.get("speed", 0))
                    )

    # --- Commandes ---------------------------------------------------------

    async def _send(self, destination: str, body: dict[str, Any] | None = None) -> None:
        if self._ws is None or self._ws.closed:
            raise JoalError("pas de connexion à JOAL")
        headers = {"destination": f"{APP_PREFIX}{destination}"}
        payload = ""
        if body is not None:
            payload = json.dumps(body)
            headers["content-type"] = "application/json"
            headers["content-length"] = str(len(payload.encode()))
        await self._ws.send_str(_frame("SEND", headers, payload))

    async def async_save_config(self, **changes: Any) -> None:
        """Envoie la configuration complète avec les champs modifiés."""
        config = {k: self.state.config[k] for k in CONFIG_KEYS if k in self.state.config}
        config.update(changes)
        await self._send("/config/save", config)

    async def async_start(self) -> None:
        await self._send("/global/start")

    async def async_stop(self) -> None:
        await self._send("/global/stop")
