"""
State Machine - Finite State Machine for Event Lifecycle
CRITICAL: All state transitions MUST go through this module
"""
from typing import Optional
from config.constants import EventState
from utils.logger import logger


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


# Define allowed state transitions as a directed graph
ALLOWED_TRANSITIONS = {
    EventState.CREATED: [
        EventState.REGISTRATION_OPEN,
        EventState.CANCELLED
    ],
    EventState.REGISTRATION_OPEN: [
        EventState.SCHEDULED,
        EventState.CANCELLED
    ],
    EventState.SCHEDULED: [
        EventState.ATTENDANCE_OPEN,
        EventState.RUNNING,  # Auto-transition if attendance window missed
        EventState.CANCELLED
    ],
    EventState.ATTENDANCE_OPEN: [
        EventState.RUNNING,
        EventState.CANCELLED
    ],
    EventState.RUNNING: [
        EventState.COMPLETED,
        EventState.CANCELLED
    ],
    EventState.COMPLETED: [
        EventState.ANALYZING
    ],
    EventState.ANALYZING: [
        EventState.REPORT_GENERATED
    ],
    EventState.REPORT_GENERATED: [],  # Terminal state
    EventState.CANCELLED: []  # Terminal state
}


class StateMachine:
    """
    Event State Machine
    Enforces valid state transitions according to the FSM definition
    """
    
    @staticmethod
    def can_transition(current_state: EventState, new_state: EventState) -> bool:
        """
        Check if transition from current_state to new_state is allowed
        
        Args:
            current_state: Current event state
            new_state: Desired new state
            
        Returns:
            True if transition is allowed, False otherwise
        """
        if current_state not in ALLOWED_TRANSITIONS:
            return False
        
        return new_state in ALLOWED_TRANSITIONS[current_state]
    
    @staticmethod
    def transition(event, new_state: EventState, reason: Optional[str] = None) -> bool:
        """
        Transition an event to a new state
        
        Args:
            event: Event model instance
            new_state: Desired new state
            reason: Optional reason for the transition (for logging)
            
        Returns:
            True if transition was successful
            
        Raises:
            InvalidStateTransitionError: If transition is not allowed
        """
        current_state = event.state
        
        # Check if transition is valid
        if not StateMachine.can_transition(current_state, new_state):
            raise InvalidStateTransitionError(
                f"Cannot transition from {current_state.value} to {new_state.value}. "
                f"Allowed transitions from {current_state.value}: "
                f"{[s.value for s in ALLOWED_TRANSITIONS[current_state]]}"
            )
        
        # Perform the transition
        old_state = current_state
        event.state = new_state
        
        # Log the transition using structured logger
        logger.log_state_transition(
            event_id=event.id if event.id else 0,
            event_name=event.name if hasattr(event, 'name') else "Unknown Event",
            old_state=old_state.value,
            new_state=new_state.value,
            reason=reason,
            triggered_by="manual" if reason and "manual" in reason.lower() else "agent"
        )
        
        return True
    
    @staticmethod
    def get_allowed_transitions(current_state: EventState) -> list[EventState]:
        """
        Get list of allowed next states from current state
        
        Args:
            current_state: Current event state
            
        Returns:
            List of allowed next states
        """
        return ALLOWED_TRANSITIONS.get(current_state, [])
    
    @staticmethod
    def is_terminal_state(state: EventState) -> bool:
        """
        Check if a state is terminal (no further transitions possible)
        
        Args:
            state: Event state to check
            
        Returns:
            True if state is terminal
        """
        return len(ALLOWED_TRANSITIONS.get(state, [])) == 0
    
    @staticmethod
    def validate_fsm() -> bool:
        """
        Validate the FSM definition (all referenced states exist)
        
        Returns:
            True if FSM is valid
            
        Raises:
            ValueError: If FSM definition is invalid
        """
        all_states = set(EventState)
        
        for state, transitions in ALLOWED_TRANSITIONS.items():
            if state not in all_states:
                raise ValueError(f"Invalid state in FSM definition: {state}")
            
            for next_state in transitions:
                if next_state not in all_states:
                    raise ValueError(f"Invalid transition target: {next_state}")
        
        return True


# Validate FSM on module import
StateMachine.validate_fsm()
