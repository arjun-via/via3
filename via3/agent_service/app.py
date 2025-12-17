from __future__ import annotations

import asyncio
import contextlib
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from .controls import RunControls
from .protocol import Event, StartSolveRequest

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


EmitFn = Callable[[Event], Awaitable[None]]


class DemoOrchestrator:
    async def run(self, request: StartSolveRequest, controls: RunControls, emit: EmitFn) -> None:
        await emit(Event(event="status", phase="start", message="starting"))
        await controls.checkpoint()
        await emit(Event(event="patch_generated", candidate=1, diff="diff --git a/foo b/foo\n"))
        await emit(Event(event="final", status="success"))


def create_app(*, orchestrator: Any | None = None) -> FastAPI:
    if load_dotenv is not None:
        load_dotenv(override=True)

    app = FastAPI()
    active_orchestrator = orchestrator or DemoOrchestrator()

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()

        try:
            start_payload = await websocket.receive_json()
            request = StartSolveRequest.from_dict(start_payload)
        except Exception as e:
            await websocket.send_json(Event(event="final", status="error", error=str(e)).to_dict())
            await websocket.close()
            return

        controls = RunControls()

        async def emit(ev: Event) -> None:
            await websocket.send_json(ev.to_dict())

        async def listen_for_controls() -> None:
            try:
                while True:
                    msg = await websocket.receive_json()
                    if not isinstance(msg, dict):
                        continue
                    msg_type = msg.get("type")
                    if msg_type == "pause":
                        controls.pause()
                    elif msg_type == "resume":
                        controls.resume()
                    elif msg_type == "cancel":
                        controls.cancel()
            except WebSocketDisconnect:
                controls.cancel()

        async def run_orchestrator() -> None:
            await active_orchestrator.run(request, controls, emit)

        listener_task = asyncio.create_task(listen_for_controls())
        try:
            await run_orchestrator()
        except WebSocketDisconnect:
            controls.cancel()
        except Exception as e:
            try:
                await emit(Event(event="final", status="error", error=str(e)))
            except Exception:
                pass
        finally:
            listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect):
                await listener_task

    return app
