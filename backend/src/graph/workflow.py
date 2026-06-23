from langgraph.graph import START, END, StateGraph
from backend.src.graph.nodes import pharma_audit_node, upload_node, cleanup_node
from backend.src.graph.state import VideoAuditState


def create_graph():
    """Build and compile the pharma video compliance LangGraph workflow."""
    workflow = StateGraph(VideoAuditState)

    # Register nodes
    workflow.add_node("upload_node", upload_node)
    workflow.add_node("pharma_audit_node", pharma_audit_node)
    workflow.add_node("cleanup_node", cleanup_node)

    # Define edges
    workflow.add_edge(START, "upload_node")
    workflow.add_edge("upload_node", "pharma_audit_node")
    workflow.add_edge("pharma_audit_node", "cleanup_node")
    workflow.add_edge("cleanup_node", END)

    return workflow.compile()


app = create_graph()
