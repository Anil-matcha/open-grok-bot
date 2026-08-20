from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.schemas.contracts import ApprovalDecision
from app.services.approval_broker import approval_broker

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])

@router.post("/respond")
async def respond_approval(decision: ApprovalDecision):
    resolved = approval_broker.resolve(decision.request_id, decision.action)
    if not resolved:
        raise HTTPException(status_code=404, detail="Approval request is no longer pending")

    action_text = "Allowed" if decision.action == "allow" else "Denied"
    return {
        "status": "ok",
        "request_id": decision.request_id,
        "action": decision.action,
        "message": f"Action has been successfully {action_text.lower()}."
    }
