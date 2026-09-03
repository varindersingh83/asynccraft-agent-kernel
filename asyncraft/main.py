"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from asynccraft.kernel.database import init_db
from asynccraft.api import router as api_router
from asynccraft.ui import router as ui_router
from asynccraft.kernel.tools import register_tool
from asynccraft.skins.ops_dispatch.tools import (
    NotifyDispatcherTool,
    RerouteTruckTool,
    UpdateDeliveryETATool,
    EscalateToManagerTool,
)
from asynccraft.skins.deal_flow.tools import (
    CreateCRMDealTool,
    SendPartnerNotificationTool,
    SchedulePartnerCallTool,
    UpdateDealStageTool,
    AddDealNoteTool,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    register_tool(NotifyDispatcherTool())
    register_tool(RerouteTruckTool())
    register_tool(UpdateDeliveryETATool())
    register_tool(EscalateToManagerTool())
    register_tool(CreateCRMDealTool())
    register_tool(SendPartnerNotificationTool())
    register_tool(SchedulePartnerCallTool())
    register_tool(UpdateDealStageTool())
    register_tool(AddDealNoteTool())
    
    yield


app = FastAPI(
    title="Asyncraft Agent Kernel",
    description="Production-shaped agent runtime with HITL approval flow",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="asynccraft/ui/static"), name="static")
app.include_router(api_router, prefix="/api")
app.include_router(ui_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
