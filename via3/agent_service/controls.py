import asyncio


class RunCancelled(Exception):
    """Raised when a run is cancelled."""


class RunControls:
    def __init__(self) -> None:
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self._cancelled = False

    def pause(self) -> None:
        self._resume_event.clear()

    def resume(self) -> None:
        self._resume_event.set()

    def cancel(self) -> None:
        self._cancelled = True
        self._resume_event.set()

    def is_cancelled(self) -> bool:
        return self._cancelled

    async def checkpoint(self) -> None:
        if self._cancelled:
            raise RunCancelled()

        await self._resume_event.wait()

        if self._cancelled:
            raise RunCancelled()

