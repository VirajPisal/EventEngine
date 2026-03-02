"""
AI Insights Service - Generate intelligent recommendations using GPT-4
Analyzes event analytics and provides actionable insights
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from models.analytics import Analytics
from models.event import Event
from config.settings import settings
from utils.logger import logger


class InsightsService:
    """Service for generating AI-powered insights using GPT-4"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        self.openai_configured = bool(settings.OPENAI_API_KEY)
        
        if self.openai_configured and OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("[INSIGHTS] OpenAI GPT-4 configured successfully")
        else:
            self.client = None
            if not OPENAI_AVAILABLE:
                logger.warning("[INSIGHTS] openai library not installed - insights will be rule-based")
            else:
                logger.warning("[INSIGHTS] OpenAI API key not configured - insights will be rule-based")
    
    def generate_insights(
        self,
        db: Session,
        event_id: int,
        analytics_data: Dict
    ) -> Dict:
        """
        Generate AI insights for an event
        
        Args:
            db: Database session
            event_id: Event ID
            analytics_data: Analytics metrics
        
        Returns:
            Dictionary with insights and recommendations
        """
        if self.client and self.openai_configured:
            return self._generate_ai_insights(analytics_data)
        else:
            return self._generate_rule_based_insights(analytics_data)
    
    def _generate_ai_insights(self, analytics_data: Dict) -> Dict:
        """
        Use GPT-4 to generate insights
        
        Args:
            analytics_data: Analytics metrics
        
        Returns:
            AI-generated insights
        """
        try:
            prompt = self._build_insights_prompt(analytics_data)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using mini for cost efficiency
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an event management analytics expert. "
                            "Analyze event performance data and provide actionable insights. "
                            "Be concise, specific, and focus on practical recommendations."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            insights_text = response.choices[0].message.content.strip()
            
            # Parse insights into structured format
            insights = self._parse_ai_response(insights_text, analytics_data)
            
            logger.info(f"[INSIGHTS] AI insights generated for event {analytics_data['event_id']}")
            
            return {
                "success": True,
                "source": "AI_GPT4",
                "insights": insights,
                "raw_text": insights_text
            }
        
        except Exception as e:
            logger.error(f"[INSIGHTS] AI generation failed: {e}")
            # Fallback to rule-based
            return self._generate_rule_based_insights(analytics_data)
    
    def _generate_rule_based_insights(self, analytics_data: Dict) -> Dict:
        """
        Generate insights using rule-based logic (fallback)
        
        Args:
            analytics_data: Analytics metrics
        
        Returns:
            Rule-based insights
        """
        insights = {
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
        
        attendance_rate = analytics_data['attendance_rate']
        confirmation_rate = analytics_data['confirmation_rate']
        no_show_rate = analytics_data['no_show_rate']
        engagement_score = analytics_data['engagement_score']
        
        # Generate summary
        insights['summary'] = (
            f"Event achieved {attendance_rate}% attendance rate with "
            f"{engagement_score}/100 engagement score. "
            f"Performance category: {analytics_data['performance_category']}."
        )
        
        # Identify strengths
        if attendance_rate >= 70:
            insights['strengths'].append("Strong attendance rate shows good event appeal")
        if confirmation_rate >= 70:
            insights['strengths'].append("High confirmation rate indicates effective communication")
        if no_show_rate < 15:
            insights['strengths'].append("Low no-show rate demonstrates reliable participants")
        
        # Identify weaknesses
        if attendance_rate < 50:
            insights['weaknesses'].append("Low attendance rate needs investigation")
        if confirmation_rate < 50:
            insights['weaknesses'].append("Poor confirmation rate suggests engagement issues")
        if no_show_rate > 30:
            insights['weaknesses'].append("High no-show rate indicates commitment problems")
        
        # Generate recommendations
        if confirmation_rate < 60:
            insights['recommendations'].append(
                "Increase reminder frequency and make confirmation process easier"
            )
        
        if no_show_rate > 20:
            insights['recommendations'].append(
                "Send confirmation reminders 24 hours before event and require double opt-in"
            )
        
        if attendance_rate < 60:
            insights['recommendations'].append(
                "Consider changing event timing, format, or adding incentives for attendance"
            )
        
        if analytics_data['total_registered'] < 20:
            insights['recommendations'].append(
                "Expand marketing efforts to increase registration numbers"
            )
        
        # Add positive reinforcement if performing well
        if engagement_score >= 80:
            insights['recommendations'].append(
                "Maintain current strategies - event is performing excellently"
            )
        
        logger.info(f"[INSIGHTS] Rule-based insights generated for event {analytics_data['event_id']}")
        
        return {
            "success": True,
            "source": "RULE_BASED",
            "insights": insights
        }
    
    def _build_insights_prompt(self, analytics_data: Dict) -> str:
        """Build prompt for GPT-4"""
        return f"""
Analyze this event performance data and provide insights:

Event: {analytics_data['event_name']}

Metrics:
- Total Registered: {analytics_data['total_registered']}
- Total Confirmed: {analytics_data['total_confirmed']} ({analytics_data['confirmation_rate']}%)
- Total Attended: {analytics_data['total_attended']} ({analytics_data['attendance_rate']}%)
- No-shows: {analytics_data['no_show_count']} ({analytics_data['no_show_rate']}%)
- Engagement Score: {analytics_data['engagement_score']}/100
- Performance: {analytics_data['performance_category']}

Provide:
1. Brief summary (2-3 sentences)
2. Key strengths (2-3 points)
3. Areas for improvement (2-3 points)
4. Actionable recommendations (3-4 specific actions)

Be concise and actionable.
"""
    
    def _parse_ai_response(self, ai_text: str, analytics_data: Dict) -> Dict:
        """Parse AI response into structured format"""
        # Simple parsing - in production, use more sophisticated NLP
        lines = ai_text.split('\n')
        
        insights = {
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if 'summary' in line.lower() or 'overview' in line.lower():
                current_section = 'summary'
                continue
            elif 'strength' in line.lower() or 'positive' in line.lower():
                current_section = 'strengths'
                continue
            elif 'weakness' in line.lower() or 'improvement' in line.lower() or 'concern' in line.lower():
                current_section = 'weaknesses'
                continue
            elif 'recommendation' in line.lower() or 'suggest' in line.lower() or 'action' in line.lower():
                current_section = 'recommendations'
                continue
            
            # Add content to current section
            if current_section == 'summary' and not line.startswith(('-', '*', '•')):
                if insights['summary']:
                    insights['summary'] += " " + line
                else:
                    insights['summary'] = line
            elif current_section in ['strengths', 'weaknesses', 'recommendations']:
                # Remove bullet points
                cleaned = line.lstrip('-*•').strip()
                if cleaned and len(cleaned) > 10:  # Filter out short fragments
                    insights[current_section].append(cleaned)
        
        # Fallback if parsing failed
        if not insights['summary']:
            insights['summary'] = f"Event achieved {analytics_data['engagement_score']}/100 engagement score."
        
        return insights
    
    def save_insights_to_analytics(
        self,
        db: Session,
        event_id: int,
        insights: Dict
    ) -> bool:
        """
        Save generated insights to Analytics table
        
        Args:
            db: Database session
            event_id: Event ID
            insights: Insights dictionary
        
        Returns:
            Success status
        """
        try:
            analytics = db.query(Analytics).filter(Analytics.event_id == event_id).first()
            
            if not analytics:
                logger.error(f"[INSIGHTS] Analytics record not found for event {event_id}")
                return False
            
            # Convert insights to JSON-friendly format
            import json
            insights_json = json.dumps(insights['insights'])
            
            analytics.ai_insights = insights_json
            analytics.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            
            logger.info(f"[INSIGHTS] Saved insights to analytics record for event {event_id}")
            return True
        
        except Exception as e:
            logger.error(f"[INSIGHTS] Failed to save insights: {e}")
            return False
    
    def format_insights_for_display(self, insights: Dict) -> str:
        """
        Format insights as human-readable text
        
        Args:
            insights: Insights dictionary
        
        Returns:
            Formatted text
        """
        insight_data = insights['insights']
        source = insights['source']
        
        output = f"\nAI Insights Report (Source: {source})\n"
        output += "=" * 60 + "\n\n"
        
        output += f"SUMMARY:\n{insight_data['summary']}\n\n"
        
        if insight_data['strengths']:
            output += "STRENGTHS:\n"
            for i, strength in enumerate(insight_data['strengths'], 1):
                output += f"  {i}. {strength}\n"
            output += "\n"
        
        if insight_data['weaknesses']:
            output += "AREAS FOR IMPROVEMENT:\n"
            for i, weakness in enumerate(insight_data['weaknesses'], 1):
                output += f"  {i}. {weakness}\n"
            output += "\n"
        
        if insight_data['recommendations']:
            output += "RECOMMENDATIONS:\n"
            for i, rec in enumerate(insight_data['recommendations'], 1):
                output += f"  {i}. {rec}\n"
            output += "\n"
        
        output += "=" * 60
        
        return output


# Singleton instance
_insights_service = None

def get_insights_service() -> InsightsService:
    """Get or create InsightsService singleton"""
    global _insights_service
    if _insights_service is None:
        _insights_service = InsightsService()
    return _insights_service
