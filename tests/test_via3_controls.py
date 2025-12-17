import asyncio

import pytest


def test_run_controls_checkpoint_passes_when_running():
    from via3.agent_service.controls import RunControls

    controls = RunControls()

    async def run():
        await asyncio.wait_for(controls.checkpoint(), timeout=0.1)

    asyncio.run(run())


def test_run_controls_checkpoint_blocks_when_paused_then_resumes():
    from via3.agent_service.controls import RunControls

    controls = RunControls()

    async def run():
        controls.pause()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(controls.checkpoint(), timeout=0.05)

        controls.resume()
        await asyncio.wait_for(controls.checkpoint(), timeout=0.1)

    asyncio.run(run())


def test_run_controls_checkpoint_raises_when_cancelled():
    from via3.agent_service.controls import RunControls, RunCancelled

    controls = RunControls()

    async def run():
        controls.cancel()
        with pytest.raises(RunCancelled):
            await controls.checkpoint()

    asyncio.run(run())

