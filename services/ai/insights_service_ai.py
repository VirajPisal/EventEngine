"""
LangChain & LangGraph - Strategic Event Insights
Analyzes event data and provides strategic suggestions via Graph reasoning.
Supports Multi-Key Failover for Groq.
"""
import json
import os
from typing import TypedDict, List, Dict, Annotated, Optional, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from config.settings import settings
from models.event import Event
from models.participant import Participant
from models.attendance import Attendance
from models.analytics import Analytics
from models.agent_action import AgentAction
from models.feedback import Feedback
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
        self.groq_keys = [k.strip() for k in settings.GROQ_API_KEYS.split(",") if k.strip()]
        self.current_key_index = 0
        self.llm = self._initialize_llm()
        self.graph = self._build_graph()

    def _initialize_llm(self) -> Optional[Any]:
        """Initialize LLM based on available keys with priority: Groq > Gemini > OpenAI"""
        # 1. Try Groq (with failover support)
        if self.groq_keys and ChatGroq:
            key = self.groq_keys[self.current_key_index]
            try:
                llm = ChatGroq(
                    model=settings.GROQ_MODEL,
                    groq_api_key=key,
                    temperature=0.2
                )
                logger.info(f"[LANGGRAPH] Configured with Groq ({settings.GROQ_MODEL}) - Key #{self.current_key_index + 1}")
                return llm
            except Exception as e:
                logger.error(f"[LANGGRAPH] Failed to init Groq key #{self.current_key_index + 1}: {e}")
                if self._rotate_key():
                    return self._initialize_llm()

        # 2. Fallback to Gemini
        if settings.GOOGLE_API_KEY and ChatGoogleGenerativeAI:
            logger.info(f"[LANGGRAPH] Falling back to Gemini ({settings.GEMINI_MODEL})")
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.2
            )

        # 3. Fallback to OpenAI
        if settings.OPENAI_API_KEY and ChatOpenAI:
            logger.info(f"[LANGGRAPH] Falling back to OpenAI ({settings.OPENAI_MODEL})")
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.2
            )

        logger.warning("[LANGGRAPH] No AI API keys configured!")
        return None

    def _rotate_key(self) -> bool:
        """Rotate to the next Groq key if available"""
        if self.current_key_index < len(self.groq_keys) - 1:
            self.current_key_index += 1
            logger.info(f"[LANGGRAPH] Rotating to Groq Key #{self.current_key_index + 1}")
            return True
        return False

    def _safe_invoke(self, prompt: List) -> Any:
        """Invoke LLM with automatic failover for Groq"""
        if not self.llm:
            raise Exception("No LLM configured")
            
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            # If it's a rate limit or token error and we are using Groq, try rotating
            if self.groq_keys and "rate_limit" in str(e).lower() or "quota" in str(e).lower():
                logger.warning(f"[LANGGRAPH] Groq Key #{self.current_key_index + 1} failed. Attempting rotation...")
                if self._rotate_key():
                    self.llm = self._initialize_llm()
                    return self._safe_invoke(prompt)
            raise e

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
        system_prompt = """
        You are a Senior Strategic Event Advisor. 
        Your goal is to analyze event data and provide a professional, highly structured strategy.
        
        USE THE FOLLOWING STRUCTURE:
        ## 📊 Problem Analysis
        (Provide a clear breakdown of the current situation and risks)
        
        ## 💡 Strategic Recommendations
        (Provide actionable steps to improve performance)
        
        ## 🚀 Next Steps
        (Specific, immediate actions)
        
        Use Markdown formatting (bolding, lists, headers). 
        Be concise, professional, and data-driven.
        """
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
        
        try:
            response = self._safe_invoke(prompt)
            state['suggestions'] = [response.content]
        except Exception as e:
            state['suggestions'] = [f"Error generating strategy: {str(e)}"]
            
        return state

    def _node_generate_actions(self, state: AgentState):
        """Node 3: Convert strategy into 3-4 concrete next steps"""
        if not self.llm:
            state['next_steps'] = ["Register more people."]
            return state
            
        suggestions = state['suggestions'][0]
        
        prompt = [
            SystemMessage(content="Convert the provided strategy into 3-4 professional, concise action items for an event organizer."),
            HumanMessage(content=f"Strategy: {suggestions}. Provide exactly 3 short action points as plain text lines.")
        ]
        
        try:
            response = self._safe_invoke(prompt)
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
        
        initial_state = {
            "event_id": event_id,
            "event_data": event_data,
            "analysis": "",
            "risk_level": "LOW",
            "suggestions": [],
            "next_steps": []
        }
        
        try:
            result = self.graph.invoke(initial_state)
            return {
                "success": True,
                "analysis": result['analysis'],
                "risk": result['risk_level'],
                "strategy": result['suggestions'][0],
                "actions": result['next_steps']
            }
        except Exception as e:
            logger.error(f"[LANGGRAPH] Analysis failed: {e}")
            return {"success": False, "error": str(e)}

# Singleton
_insights_service_ai = None
def get_insights_service_ai() -> LangGraphInsightsService:
    global _insights_service_ai
    if _insights_service_ai is None:
        _insights_service_ai = LangGraphInsightsService()
    return _insights_service_ai
