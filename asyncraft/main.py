"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from asyncraft.kernel.database import init_db
from asyncraft.api import router as api_router
from asyncraft.ui import router as ui_router
from asyncraft.kernel.tools import register_tool
from asyncraft.skins.ops_dispatch.tools import (
    NotifyDispatcherTool,
    RerouteTruckTool,
    UpdateDeliveryETATool,
    EscalateToManagerTool,
)
from asyncraft.skins.deal_flow.tools import (
    CreateCRMDealTool,
    SendPartnerNotificationTool,
    SchedulePartnerCallTool,
    UpdateDealStageTool,
    AddDealNoteTool,
)
from asyncraft.skins.crm_followup.tools import (
    AssessLeadScoreTool,
    ApproveEmailDraftTool,
    CheckManagerReviewNeededTool,
    UpdateCRMStageTool,
)
from asyncraft.skins.invoice_ap.tools import (
    AssessThreeWayMatchTool,
    ApproveAPCorrectionTool,
    CheckVendorComplianceTool,
    PostToAPTool,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    # Register ops_dispatch tools
    register_tool(NotifyDispatcherTool())
    register_tool(RerouteTruckTool())
    register_tool(UpdateDeliveryETATool())
    register_tool(EscalateToManagerTool())
    
    # Register deal_flow tools
    register_tool(CreateCRMDealTool())
    register_tool(SendPartnerNotificationTool())
    register_tool(SchedulePartnerCallTool())
    register_tool(UpdateDealStageTool())
    register_tool(AddDealNoteTool())
    
    # Register crm_followup tools
    register_tool(AssessLeadScoreTool())
    register_tool(ApproveEmailDraftTool())
    register_tool(CheckManagerReviewNeededTool())
    register_tool(UpdateCRMStageTool())
    
    # Register invoice_ap tools
    register_tool(AssessThreeWayMatchTool())
    register_tool(ApproveAPCorrectionTool())
    register_tool(CheckVendorComplianceTool())
    register_tool(PostToAPTool())
    
    yield


app = FastAPI(
    title="Asyncraft Agent Kernel — SME Ops Demos",
    description="Production-shaped agent runtime with HITL approval flow for freight dispatch, CRM follow-up, and invoice/AP workflows",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="asyncraft/ui/static"), name="static")
app.include_router(api_router, prefix="/api")
app.include_router(ui_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
