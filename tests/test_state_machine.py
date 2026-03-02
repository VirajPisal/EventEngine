"""
Unit tests for State Machine
"""
import pytest
from config.constants import EventState
from core.state_machine import StateMachine, InvalidStateTransitionError, ALLOWED_TRANSITIONS
from models.event import Event
from datetime import datetime, timedelta


class TestStateMachine:
    """Test suite for state machine functionality"""
    
    def test_fsm_validation(self):
        """Test that FSM definition is valid"""
        assert StateMachine.validate_fsm() is True
    
    def test_allowed_transitions(self):
        """Test that allowed transitions are correctly defined"""
        # CREATED can transition to REGISTRATION_OPEN and CANCELLED
        assert EventState.REGISTRATION_OPEN in ALLOWED_TRANSITIONS[EventState.CREATED]
        assert EventState.CANCELLED in ALLOWED_TRANSITIONS[EventState.CREATED]
        
        # REPORT_GENERATED is terminal
        assert len(ALLOWED_TRANSITIONS[EventState.REPORT_GENERATED]) == 0
    
    def test_can_transition_valid(self):
        """Test valid transition check"""
        # Valid transition
        assert StateMachine.can_transition(
            EventState.CREATED, 
            EventState.REGISTRATION_OPEN
        ) is True
    
    def test_can_transition_invalid(self):
        """Test invalid transition check"""
        # Invalid transition (skipping states)
        assert StateMachine.can_transition(
            EventState.CREATED, 
            EventState.COMPLETED
        ) is False
    
    def test_valid_state_transition(self):
        """Test successful state transition"""
        # Create a mock event
        event = Event(
            name="Test Event",
            event_type="OFFLINE",
            state=EventState.CREATED,
            start_time=datetime.utcnow() + timedelta(days=7),
            end_time=datetime.utcnow() + timedelta(days=7, hours=2)
        )
        
        # Transition should succeed
        result = StateMachine.transition(event, EventState.REGISTRATION_OPEN)
        assert result is True
        assert event.state == EventState.REGISTRATION_OPEN
    
    def test_invalid_state_transition(self):
        """Test that invalid transition raises error"""
        event = Event(
            name="Test Event",
            event_type="OFFLINE",
            state=EventState.CREATED,
            start_time=datetime.utcnow() + timedelta(days=7),
            end_time=datetime.utcnow() + timedelta(days=7, hours=2)
        )
        
        # Try invalid transition
        with pytest.raises(InvalidStateTransitionError):
            StateMachine.transition(event, EventState.COMPLETED)
    
    def test_get_allowed_transitions(self):
        """Test getting list of allowed transitions"""
        allowed = StateMachine.get_allowed_transitions(EventState.CREATED)
        assert EventState.REGISTRATION_OPEN in allowed
        assert EventState.CANCELLED in allowed
    
    def test_is_terminal_state(self):
        """Test terminal state detection"""
        assert StateMachine.is_terminal_state(EventState.REPORT_GENERATED) is True
        assert StateMachine.is_terminal_state(EventState.CANCELLED) is True
        assert StateMachine.is_terminal_state(EventState.CREATED) is False
    
    def test_full_lifecycle_path(self):
        """Test complete lifecycle state transitions"""
        event = Event(
            name="Full Lifecycle Event",
            event_type="OFFLINE",
            state=EventState.CREATED,
            start_time=datetime.utcnow() + timedelta(days=7),
            end_time=datetime.utcnow() + timedelta(days=7, hours=2)
        )
        
        # Follow complete path
        StateMachine.transition(event, EventState.REGISTRATION_OPEN)
        assert event.state == EventState.REGISTRATION_OPEN
        
        StateMachine.transition(event, EventState.SCHEDULED)
        assert event.state == EventState.SCHEDULED
        
        StateMachine.transition(event, EventState.ATTENDANCE_OPEN)
        assert event.state == EventState.ATTENDANCE_OPEN
        
        StateMachine.transition(event, EventState.RUNNING)
        assert event.state == EventState.RUNNING
        
        StateMachine.transition(event, EventState.COMPLETED)
        assert event.state == EventState.COMPLETED
        
        StateMachine.transition(event, EventState.ANALYZING)
        assert event.state == EventState.ANALYZING
        
        StateMachine.transition(event, EventState.REPORT_GENERATED)
        assert event.state == EventState.REPORT_GENERATED
        
        # Now in terminal state
        assert StateMachine.is_terminal_state(event.state) is True
    
    def test_cancellation_from_any_active_state(self):
        """Test that events can be cancelled from most states"""
        for state in [EventState.CREATED, EventState.REGISTRATION_OPEN, 
                      EventState.SCHEDULED, EventState.RUNNING]:
            event = Event(
                name="Test Event",
                event_type="OFFLINE",
                state=state,
                start_time=datetime.utcnow() + timedelta(days=7),
                end_time=datetime.utcnow() + timedelta(days=7, hours=2)
            )
            
            if EventState.CANCELLED in ALLOWED_TRANSITIONS[state]:
                StateMachine.transition(event, EventState.CANCELLED)
                assert event.state == EventState.CANCELLED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
