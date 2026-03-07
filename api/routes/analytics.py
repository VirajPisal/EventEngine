"""
Analytics Routes
Endpoints for event analytics, AI insights, and reporting
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List

from db.base import get_db_context
from services.analytics_service import AnalyticsService
from services.insights_service import get_insights_service
from utils.logger import logger


router = APIRouter()


# Request/Response Models
class GenerateAnalyticsRequest(BaseModel):
    event_id: int = Field(..., ge=1)


class CompareEventsRequest(BaseModel):
    event_ids: List[int] = Field(..., min_length=2, max_length=10)


# Endpoints
@router.post("/calculate")
async def calculate_analytics(request: GenerateAnalyticsRequest):
    """
    Calculate analytics for an event
    
    - **event_id**: Event ID
    
    Calculates attendance rates, engagement scores, and performance metrics
    """
    try:
        with get_db_context() as db:
            result = AnalyticsService.calculate_event_analytics(
                db=db,
                event_id=request.event_id
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            # Save analytics to database
            save_result = AnalyticsService.save_analytics(
                db=db,
                event_id=request.event_id,
                analytics_data=result["analytics"]
            )
            
            logger.info(f"[API] Calculated analytics for event {request.event_id}")
            
            return {
                "success": True,
                "message": "Analytics calculated successfully",
                "analytics": result["analytics"],
                "saved": save_result["success"]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to calculate analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate analytics: {str(e)}")


@router.get("/event/{event_id}")
async def get_event_analytics(event_id: int):
    """
    Get saved analytics for an event
    
    - **event_id**: Event ID
    """
    try:
        with get_db_context() as db:
            analytics = AnalyticsService.get_event_analytics(db, event_id)
            
            if not analytics:
                raise HTTPException(status_code=404, detail="Analytics not found for this event")
            
            return {
                "success": True,
                "event_id": event_id,
                "analytics": analytics
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get analytics for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.post("/insights/generate")
async def generate_insights(request: GenerateAnalyticsRequest):
    """
    Generate AI insights for an event
    
    - **event_id**: Event ID
    
    Uses GPT-4 (if configured) or rule-based analysis to generate recommendations
    """
    try:
        with get_db_context() as db:
            # First calculate analytics
            analytics_result = AnalyticsService.calculate_event_analytics(
                db=db,
                event_id=request.event_id
            )
            
            if not analytics_result["success"]:
                raise HTTPException(status_code=400, detail=analytics_result["message"])
            
            # Generate insights
            insights_service = get_insights_service()
            insights_result = insights_service.generate_insights(
                db=db,
                event_id=request.event_id,
                analytics_data=analytics_result["analytics"]
            )
            
            if not insights_result["success"]:
                raise HTTPException(status_code=500, detail="Failed to generate insights")
            
            # Save insights
            insights_service.save_insights_to_analytics(
                db=db,
                event_id=request.event_id,
                insights=insights_result
            )
            
            logger.info(f"[API] Generated insights for event {request.event_id}")
            
            return {
                "success": True,
                "message": "Insights generated successfully",
                "source": insights_result["source"],
                "insights": insights_result["insights"]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to generate insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


@router.get("/insights/{event_id}")
async def get_event_insights(event_id: int):
    """
    Get saved AI insights for an event
    
    - **event_id**: Event ID
    """
    try:
        with get_db_context() as db:
            analytics = AnalyticsService.get_event_analytics(db, event_id)
            
            if not analytics:
                raise HTTPException(status_code=404, detail="Analytics not found for this event")
            
            if not analytics.get("ai_insights"):
                raise HTTPException(status_code=404, detail="No insights generated for this event")
            
            # Parse JSON string if needed
            import json
            insights_data = analytics["ai_insights"]
            if isinstance(insights_data, str):
                insights_data = json.loads(insights_data)
            
            return {
                "success": True,
                "event_id": event_id,
                "insights": insights_data
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get insights for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.post("/compare")
async def compare_events(request: CompareEventsRequest):
    """
    Compare analytics across multiple events
    
    - **event_ids**: List of event IDs (2-10 events)
    
    Returns comparison with averages and best/worst performers
    """
    try:
        with get_db_context() as db:
            result = AnalyticsService.compare_events(
                db=db,
                event_ids=request.event_ids
            )
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            logger.info(f"[API] Compared {len(request.event_ids)} events")
            
            return {
                "success": True,
                "message": f"Compared {result['events_compared']} events",
                "comparison": {
                    "events_compared": result["events_compared"],
                    "averages": result["averages"],
                    "best_performer": result.get("best_performer"),
                    "worst_performer": result.get("worst_performer"),
                    "events": result["events"]
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to compare events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compare events: {str(e)}")


@router.get("/report/{event_id}")
async def get_event_report(event_id: int):
    """
    Get comprehensive text report for an event
    
    - **event_id**: Event ID
    
    Returns formatted text report with all metrics
    """
    try:
        with get_db_context() as db:
            report = AnalyticsService.generate_summary_report(
                db=db,
                event_id=event_id
            )
            
            if not report:
                raise HTTPException(status_code=404, detail="Unable to generate report for this event")
            
            return {
                "success": True,
                "event_id": event_id,
                "report": report,
                "format": "text/plain"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to generate report for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/dashboard")
async def get_dashboard_stats(
    limit: int = Query(10, ge=1, le=50, description="Number of recent events to include")
):
    """
    Get dashboard statistics across all events
    
    - **limit**: Number of recent events to analyze (1-50, default 10)
    """
    try:
        with get_db_context() as db:
            # Get recent events with analytics
            from models.event import Event
            from models.analytics import Analytics
            
            events = db.query(Event).order_by(Event.created_at.desc()).limit(limit).all()
            
            total_events = len(events)
            total_participants = 0
            total_attended = 0
            avg_engagement = 0
            
            event_stats = []
            
            for event in events:
                analytics = AnalyticsService.get_event_analytics(db, event.id)
                if analytics:
                    total_participants += analytics.get("total_registered", 0)
                    total_attended += analytics.get("total_attended", 0)
                    avg_engagement += analytics.get("engagement_score", 0)
                    
                    event_stats.append({
                        "id": event.id,
                        "name": event.name,
                        "state": event.state.value,
                        "attendance_rate": analytics.get("attendance_rate", 0),
                        "engagement_score": analytics.get("engagement_score", 0)
                    })
            
            if total_events > 0:
                avg_engagement = avg_engagement / total_events
            
            return {
                "success": True,
                "dashboard": {
                    "total_events": total_events,
                    "total_participants": total_participants,
                    "total_attended": total_attended,
                    "overall_attendance_rate": round((total_attended / total_participants * 100) if total_participants > 0 else 0, 2),
                    "average_engagement": round(avg_engagement, 2),
                    "recent_events": event_stats
                }
            }
    
    except Exception as e:
        logger.error(f"[API] Failed to get dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")
