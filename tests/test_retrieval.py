from graph_rag_poc.retrieval import KnowledgeGraphIndex
from graph_rag_poc.seed_data import get_demo_use_case


def test_graph_retrieval_expands_beyond_vector_baseline() -> None:
    use_case = get_demo_use_case()
    index = KnowledgeGraphIndex(use_case.nodes, use_case.edges)
    question = "How are the VPN exploit alerts connected to the ransomware on fs-02?"

    vector = index.retrieve(question, mode="vector", top_k=6)
    graph = index.retrieve(question, mode="graph", top_k=6)

    vector_ids = {candidate.node_id for candidate in vector.candidates}
    graph_ids = {candidate.node_id for candidate in graph.candidates}

    assert "asset_jump_01" in graph_ids
    assert "technique_t1059_001" in graph_ids
    assert graph_ids != vector_ids
    assert len(graph.paths) >= 1


def test_action_question_pulls_controls_into_graph_result() -> None:
    use_case = get_demo_use_case()
    index = KnowledgeGraphIndex(use_case.nodes, use_case.edges)
    question = "What should the SOC do in the next four hours to contain Operation Night Lantern?"

    graph = index.retrieve(question, mode="graph", top_k=6)
    graph_ids = {candidate.node_id for candidate in graph.candidates}

    assert "control_patch_gateway" in graph_ids
    assert "control_reset_accounts" in graph_ids

