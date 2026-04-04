"""
Agent Routes - Pending action approval/rejection for organizer
"""
import json
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import Optional

from db.base import get_db_context
from models.agent_action import AgentAction
from models.event import Event
from api.deps import get_current_organizer
from services.reminder_service import ReminderService
from utils.logger import logger

router = APIRouter()


@router.get("/pending-actions")
async def get_pending_actions(
    event_id: Optional[int] = Query(None),
    user: dict = Depends(get_current_organizer),
):
    """Get all pending agent actions, optionally filtered by event_id"""
    try:
        with get_db_context() as db:
            query = db.query(AgentAction).filter(AgentAction.status == "PENDING")
            if event_id:
                query = query.filter(AgentAction.event_id == event_id)
            actions = query.order_by(AgentAction.created_at.desc()).all()

            return {
                "success": True,
                "count": len(actions),
                "actions": [
                    {
                        "id": a.id,
                        "event_id": a.event_id,
                        "action_type": a.action_type,
                        "description": a.description,
                        "payload_json": a.payload_json,
                        "status": a.status,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in actions
                ],
            }
    except Exception as e:
        logger.error(f"[AGENT-API] Failed to get pending actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/approve")
async def approve_action(
    action_id: int,
    user: dict = Depends(get_current_organizer),
):
    """Approve and execute a pending agent action"""
    try:
        with get_db_context() as db:
            action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
            if not action:
                raise HTTPException(status_code=404, detail="Action not found")
            if action.status != "PENDING":
                raise HTTPException(status_code=400, detail=f"Action already {action.status}")

            # Execute the action
            executed = False
            if action.action_type == "SEND_REMINDER" and action.payload_json:
                payload = json.loads(action.payload_json)
                result = ReminderService.evaluate_and_send_reminders(
                    db, payload["event_id"], force=True
                )
                executed = result.get("sent", False)

            action.status = "EXECUTED" if executed else "APPROVED"
            action.executed_at = datetime.now(timezone.utc)

            logger.info(f"[AGENT-API] Action #{action_id} approved by {user.get('name')}")
            return {
                "success": True,
                "message": f"Action {'executed' if executed else 'approved'}",
                "action_id": action_id,
                "status": action.status,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AGENT-API] Failed to approve action {action_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/reject")
async def reject_action(
    action_id: int,
    user: dict = Depends(get_current_organizer),
):
    """Reject a pending agent action"""
    try:
        with get_db_context() as db:
            action = db.query(AgentAction).filter(AgentAction.id == action_id).first()
            if not action:
                raise HTTPException(status_code=404, detail="Action not found")
            if action.status != "PENDING":
                raise HTTPException(status_code=400, detail=f"Action already {action.status}")

            action.status = "REJECTED"
            action.executed_at = datetime.now(timezone.utc)

            logger.info(f"[AGENT-API] Action #{action_id} rejected by {user.get('name')}")
            return {
                "success": True,
                "message": "Action rejected",
                "action_id": action_id,
                "status": "REJECTED",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AGENT-API] Failed to reject action {action_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-actions")
async def get_recent_actions(
    event_id: Optional[int] = Query(None),
    user: dict = Depends(get_current_organizer),
):
    """Get last 10 executed/rejected actions"""
    try:
        with get_db_context() as db:
            query = db.query(AgentAction).filter(
                AgentAction.status.in_(["EXECUTED", "APPROVED", "REJECTED"])
            )
            if event_id:
                query = query.filter(AgentAction.event_id == event_id)
            actions = query.order_by(AgentAction.executed_at.desc()).limit(10).all()

            return {
                "success": True,
                "count": len(actions),
                "actions": [
                    {
                        "id": a.id,
                        "event_id": a.event_id,
                        "action_type": a.action_type,
                        "description": a.description,
                        "status": a.status,
                        "created_at": a.created_at.isoformat(),
                        "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                    }
                    for a in actions
                ],
            }
    except Exception as e:
        logger.error(f"[AGENT-API] Failed to get recent actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/{event_id}")
async def get_event_insights(
    event_id: int,
    user: dict = Depends(get_current_organizer),
):
    """Get AI strategic insights for a specific event using LangGraph"""
    try:
        from services.ai.insights_service_ai import get_insights_service_ai
        with get_db_context() as db:
            service = get_insights_service_ai()
            result = service.run_analysis(db, event_id)
            
            if not result.get("success"):
                raise HTTPException(status_code=500, detail=result.get("error", "AI analysis failed"))
            
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AGENT-API] Failed to generate AI insights for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
