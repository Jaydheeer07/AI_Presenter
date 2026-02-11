"""LangGraph state machine definition for the DexIQ AI Presenter.

The graph routes between nodes based on the current agent state and
the next command in the queue. Each node corresponds to a presentation
state (IDLE, INTRODUCING, PRESENTING, ASKING, etc.).
"""

import logging

from langgraph.graph import END, StateGraph

from backend.agent.actions import (
    asking_node,
    decide_next_state,
    idle_node,
    introducing_node,
    outro_node,
    presenting_node,
    qa_mode_node,
    responding_node,
    route_next_command,
    transitioning_node,
    waiting_answer_node,
)
from backend.agent.states import GraphState

logger = logging.getLogger(__name__)


def build_presentation_graph() -> StateGraph:
    """Build and compile the LangGraph state machine for the presentation.

    State flow:
        IDLE → (command) → INTRODUCING → router → PRESENTING → router → ...
        Any state can be interrupted by /pause → PAUSED → /resume → previous state
        OUTRO → DONE (END)

    Returns:
        Compiled LangGraph state machine.
    """
    graph = StateGraph(GraphState)

    # Add all state nodes
    graph.add_node("idle", idle_node)
    graph.add_node("introducing", introducing_node)
    graph.add_node("presenting", presenting_node)
    graph.add_node("asking", asking_node)
    graph.add_node("waiting_answer", waiting_answer_node)
    graph.add_node("responding", responding_node)
    graph.add_node("transitioning", transitioning_node)
    graph.add_node("qa_mode", qa_mode_node)
    graph.add_node("outro", outro_node)
    graph.add_node("router", route_next_command)

    # Set entry point
    graph.set_entry_point("router")

    # After each action node completes, go to the router to check for next command
    graph.add_edge("idle", END)
    graph.add_edge("introducing", END)
    graph.add_edge("presenting", END)
    graph.add_edge("asking", END)
    graph.add_edge("waiting_answer", END)
    graph.add_edge("responding", END)
    graph.add_edge("transitioning", END)
    graph.add_edge("qa_mode", END)
    graph.add_edge("outro", END)

    # Router decides which state node to go to next
    graph.add_conditional_edges("router", decide_next_state, {
        "idle": "idle",
        "introducing": "introducing",
        "presenting": "presenting",
        "asking": "asking",
        "waiting_answer": "waiting_answer",
        "responding": "responding",
        "transitioning": "transitioning",
        "qa_mode": "qa_mode",
        "outro": "outro",
        "__end__": END,
    })

    return graph.compile()


# Singleton compiled graph
presentation_graph = build_presentation_graph()
