from fastapi import APIRouter

from ..schemas import PollingStatusResponse
from ..browser.monitor import monitor

router = APIRouter(tags=["polling"])


@router.post("/polling/start")
async def start_polling():
    """Start the message monitoring loop."""
    if monitor.running:
        return {"status": "already_running"}
    await monitor.start()
    return {"status": "started"}


@router.post("/polling/stop")
async def stop_polling():
    """Stop the message monitoring loop."""
    if not monitor.running:
        return {"status": "already_stopped"}
    await monitor.stop()
    return {"status": "stopped"}


@router.get("/polling/status", response_model=PollingStatusResponse)
async def polling_status():
    """Get current polling state."""
    return PollingStatusResponse(
        running=monitor.running,
        cycle_count=monitor.cycle_count,
        last_poll_at=monitor.last_poll_at,
        errors=list(monitor.recent_errors),
    )


@router.post("/browser/login")
async def browser_login():
    """Open headed browser for Facebook login."""
    from ..browser.auth import login_to_facebook

    result = await login_to_facebook()
    return result
