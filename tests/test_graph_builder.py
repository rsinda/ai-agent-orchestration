from backend.app.runtime.graph_builder import GraphBuilder


def test_condition_can_match_previous_agent_output_case_insensitively():
    builder = GraphBuilder()
    state = {"messages": [{"sender_id": "triage", "content": "MATH"}]}

    assert builder._condition_matches("Math", state)
    assert builder._condition_matches("output_equals:math", state)


def test_condition_can_match_previous_agent_output_contains_prefix():
    builder = GraphBuilder()
    state = {"messages": [{"sender_id": "triage", "content": "Route to MATH agent"}]}

    assert builder._condition_matches("output_contains:MATH", state)
    assert not builder._condition_matches("Math", state)
