"""
LangChain & LangGraph - Strategic Event Insights
Analyzes event data and provides strategic suggestions via Graph reasoning.
"""
import json
from typing import TypedDict, List, Dict, Annotated
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from config.settings import settings
from models.event import Event
from models.participant import Participant
from config.constants import EventState
from utils.logger import logger

# Define the state of our graph
class AgentState(TypedDict):
    event_id: int
    event_data: Dict
    analysis: str
    risk_level: str  # LOW, MEDIUM, HIGH
    suggestions: List[str]
    next_steps: List[str]

class LangGraphInsightsService:
    def __init__(self):
        self.llm = None
        if settings.GOOGLE_API_KEY:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.2
            )
            logger.info(f"[LANGGRAPH] Configured with {settings.GEMINI_MODEL}")
        elif settings.OPENAI_API_KEY:
            self.llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.2
            )
            logger.info(f"[LANGGRAPH] Configured with {settings.OPENAI_MODEL}")
            
        self.graph = self._build_graph()

    def _build_graph(self):
        """Construct the strategic reasoning graph"""
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("analyze_data", self._node_analyze_data)
        workflow.add_node("reason_strategy", self._node_reason_strategy)
        workflow.add_node("generate_actions", self._node_generate_actions)
        
        # Define flow
        workflow.set_entry_point("analyze_data")
        workflow.add_edge("analyze_data", "reason_strategy")
        workflow.add_edge("reason_strategy", "generate_actions")
        workflow.add_edge("generate_actions", END)
        
        return workflow.compile()

    def _node_analyze_data(self, state: AgentState):
        """Node 1: Extract insights from raw data"""
        data = state['event_data']
        
        # Internal analytics logic (could be done by LLM too)
        capacity = data.get('max_participants') or 100
        registered = data.get('registered') or 0
        rem_days = data.get('days_remaining') or 0
        
        fill_rate = (registered / capacity) * 100
        
        risk = "LOW"
        if rem_days < 7 and fill_rate < 50:
            risk = "HIGH"
        elif rem_days < 14 and fill_rate < 30:
            risk = "MEDIUM"
            
        state['analysis'] = f"The event is {fill_rate:.1f}% full with {rem_days} days remaining."
        state['risk_level'] = risk
        return state

    def _node_reason_strategy(self, state: AgentState):
        """Node 2: Brainstorm strategy based on risks"""
        if not self.llm:
            state['suggestions'] = ["LLM not configured. Check registration numbers."]
            return state
            
        risk = state['risk_level']
        analysis = state['analysis']
        event_name = state['event_data'].get('name')
        
        prompt = [
            SystemMessage(content="You are an Event Strategist Agent. Think about what actions would increase registrations or engagement."),
            HumanMessage(content=f"Event: {event_name}. Problem: {analysis}. Risk Level: {risk}. Why might this be happening and what strategic approach should we take?")
        ]
        
        response = self.llm.invoke(prompt)
        state['suggestions'] = [response.content]
        return state

    def _node_generate_actions(self, state: AgentState):
        """Node 3: Convert strategy into 3-4 concrete next steps"""
        if not self.llm:
            state['next_steps'] = ["Register more people."]
            return state
            
        suggestions = state['suggestions'][0]
        
        prompt = [
            SystemMessage(content="Convert the provided strategy into 3-4 professional, concise action items for an event organizer."),
            HumanMessage(content=f"Strategy: {suggestions}. Provide exactly 3 short action points as JSON list strings.")
        ]
        
        try:
            # We want structured output for the list
            response = self.llm.invoke(prompt)
            # Simple list cleaning if not valid JSON
            steps = [s.strip('- ').strip() for s in response.content.split('\n') if len(s) > 5]
            state['next_steps'] = steps[:4]
        except:
            state['next_steps'] = ["Review marketing", "Notify VIPs", "Check capacities"]
            
        return state

    def run_analysis(self, db: Session, event_id: int):
        """Main entry point to get insights"""
        event = db.query(Event).get(event_id)
        if not event:
            return {"error": "Event not found"}
            
        # Gather metrics
        from services.registration_service import RegistrationService
        stats = RegistrationService.get_participant_stats(db, event_id)
        
        now = datetime.now(timezone.utc)
        start_time = event.start_time.replace(tzinfo=timezone.utc)
        days_rem = (start_time - now).days
        
        event_data = {
            "name": event.name,
            "registered": stats['total_registered'],
            "max_participants": event.max_participants,
            "days_remaining": max(0, days_rem),
            "state": event.state.value
        }
        
        # Run LangGraph
        initial_state = {
            "event_id": event_id,
            "event_data": event_data,
            "analysis": "",
            "risk_level": "LOW",
            "suggestions": [],
            "next_steps": []
        }
        
        result = self.graph.invoke(initial_state)
        
        return {
            "success": True,
            "analysis": result['analysis'],
            "risk": result['risk_level'],
            "strategy": result['suggestions'][0],
            "actions": result['next_steps']
        }

# Singleton
_insights_service_ai = None
def get_insights_service_ai() -> LangGraphInsightsService:
    global _insights_service_ai
    if _insights_service_ai is None:
        _insights_service_ai = LangGraphInsightsService()
    return _insights_service_ai
