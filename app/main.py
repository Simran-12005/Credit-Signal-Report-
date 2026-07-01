"""Credit Signal Report — standalone FastAPI app (Part A: data collection)."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import get_settings
from app.routers import (
    buyers,
    features,
    gst,
    health,
    mca,
    orders,
    payment_import,
    reports,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Credit Signal Report",
    description="GSTIN-based credit-risk data collection (standalone).",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(reports.router)
app.include_router(features.router)
app.include_router(buyers.router)
app.include_router(orders.router)
app.include_router(payment_import.router)
app.include_router(gst.router)
app.include_router(mca.router)


@app.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    """Credit report dashboard UI (run a GSTIN, view + share the report)."""
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/simulator", include_in_schema=False)
async def simulator() -> FileResponse:
    """Manual payment-history simulator UI."""
    return FileResponse(STATIC_DIR / "simulator.html")


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.is_dev,
    )
