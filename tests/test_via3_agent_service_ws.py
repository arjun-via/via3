import asyncio

from fastapi.testclient import TestClient


def test_agent_service_websocket_streams_events_in_order():
    from via3.agent_service.app import create_app
    from via3.agent_service.protocol import Event

    class FakeOrchestrator:
        async def run(self, request, controls, emit):
            await emit(Event(event="status", phase="start", message="starting"))
            await emit(Event(event="status", phase="done", message="done"))
            await emit(Event(event="final", status="success"))

    app = create_app(orchestrator=FakeOrchestrator())

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"task": "test task"})

            ev1 = ws.receive_json()
            assert ev1["event"] == "status"
            assert ev1["phase"] == "start"

            ev2 = ws.receive_json()
            assert ev2["event"] == "status"
            assert ev2["phase"] == "done"

            ev3 = ws.receive_json()
            assert ev3["event"] == "final"
            assert ev3["status"] == "success"


def test_agent_service_websocket_cancel_stops_run():
    from via3.agent_service.app import create_app
    from via3.agent_service.controls import RunCancelled
    from via3.agent_service.protocol import Event

    class CancelAwareOrchestrator:
        async def run(self, request, controls, emit):
            await emit(Event(event="status", phase="start", message="starting"))
            try:
                while True:
                    await controls.checkpoint()
                    await asyncio.sleep(0.01)
            except RunCancelled:
                await emit(Event(event="final", status="cancelled"))

    app = create_app(orchestrator=CancelAwareOrchestrator())

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"task": "test task"})
            first = ws.receive_json()
            assert first["event"] == "status"

            ws.send_json({"type": "cancel"})
            final = ws.receive_json()
            assert final["event"] == "final"
            assert final["status"] == "cancelled"

