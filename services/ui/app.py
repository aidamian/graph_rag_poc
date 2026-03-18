from __future__ import annotations

import os

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def get_json(path: str) -> dict:
    response = httpx.get(f"{API_BASE_URL}{path}", timeout=30.0)
    response.raise_for_status()
    return response.json()


def post_json(path: str, payload: dict) -> dict:
    response = httpx.post(f"{API_BASE_URL}{path}", json=payload, timeout=60.0)
    response.raise_for_status()
    return response.json()


def graphviz_for(mode_payload: dict | None) -> str:
    if not mode_payload:
        return "graph G { label=\"No graph available\"; }"

    node_colors = {
        "Alert": "#d1495b",
        "Asset": "#2e86ab",
        "Campaign": "#6c4ab6",
        "Control": "#2a9d8f",
        "Document": "#8d99ae",
        "Incident": "#e76f51",
        "Organization": "#6d597a",
        "Product": "#264653",
        "Technique": "#f4a261",
        "ThreatActor": "#c44536",
        "Vulnerability": "#8f2d56",
    }

    nodes = mode_payload["retrieval"]["subgraph_nodes"]
    edges = mode_payload["retrieval"]["subgraph_edges"]
    lines = [
        "graph G {",
        'rankdir="LR";',
        'bgcolor="transparent";',
        'node [shape="box", style="rounded,filled", fontname="IBM Plex Sans"];',
        'edge [fontname="IBM Plex Sans"];',
    ]
    for node in nodes:
        label = f'{node["name"]}\\n{node["kind"]}'
        color = node_colors.get(node["kind"], "#457b9d")
        lines.append(
            f'"{node["id"]}" [label="{label}", fillcolor="{color}", fontcolor="white"];'
        )
    for edge in edges:
        lines.append(
            f'"{edge["source"]}" -- "{edge["target"]}" [label="{edge["type"]}"];'
        )
    lines.append("}")
    return "\n".join(lines)


st.set_page_config(
    page_title="Cyber Graph RAG PoC",
    page_icon=":satellite:",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(244, 162, 97, 0.18), transparent 34%),
            radial-gradient(circle at top right, rgba(42, 157, 143, 0.16), transparent 30%),
            linear-gradient(180deg, #f6f4ef 0%, #fbfaf7 100%);
        color: #172026;
    }
    .hero {
        padding: 1.2rem 1.4rem;
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(23,32,38,0.96), rgba(38,70,83,0.92));
        color: white;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 18px 40px rgba(23,32,38,0.15);
    }
    .callout {
        padding: 1rem 1.1rem;
        border-radius: 18px;
        background: rgba(255,255,255,0.78);
        border: 1px solid rgba(23,32,38,0.08);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

summary = get_json("/summary")
use_case = summary["use_case"]

st.markdown(
    f"""
    <div class="hero">
      <h1 style="margin-bottom:0.4rem;">Cyber Graph RAG PoC</h1>
      <p style="font-size:1.05rem; margin-bottom:0.8rem;">
        {use_case["description"]}
      </p>
      <p style="margin:0; opacity:0.88;">
        Compare Graph RAG against vector-only retrieval on a single end-to-end ransomware investigation.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
metric_col_1.metric("Entities", summary["node_count"])
metric_col_2.metric("Relationships", summary["edge_count"])
metric_col_3.metric("Suggested Questions", len(use_case["suggested_questions"]))

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.subheader("Investigation Copilot")
    selected_question = st.selectbox(
        "Suggested prompts",
        options=list(use_case["suggested_questions"]),
        index=0,
    )
    question = st.text_area(
        "Question",
        value=selected_question,
        height=120,
    )
    mode = st.selectbox(
        "Retrieval mode",
        options=["compare", "graph", "vector"],
        index=0,
        help="Compare shows graph-aware and vector-only retrieval side by side.",
    )
    top_k = st.slider("Top entities to keep", min_value=4, max_value=12, value=8)

    if st.button("Run Investigation", type="primary", use_container_width=True):
        with st.spinner("Querying the Graph RAG service..."):
            result = post_json("/ask", {"question": question, "mode": mode, "top_k": top_k})
        st.session_state["result"] = result

with right:
    st.subheader("Why This Demo Exists")
    st.markdown('<div class="callout">', unsafe_allow_html=True)
    for goal in use_case["learning_goals"]:
        st.write(f"- {goal}")
    st.markdown("</div>", unsafe_allow_html=True)
    st.subheader("Incident Storyline")
    for step in use_case["storyline"]:
        st.write(f"- {step}")

result = st.session_state.get("result")

if result:
    st.subheader("Results")
    if result.get("comparison"):
        st.info(result["comparison"])

    graph_col, vector_col = st.columns(2)
    for label, payload, container in (
        ("Graph RAG", result.get("graph"), graph_col),
        ("Vector Baseline", result.get("vector"), vector_col),
    ):
        if not payload:
            continue
        with container:
            st.markdown(f"### {label}")
            st.write(payload["answer"]["answer"])
            st.write("Provider:", payload["answer"]["provider"])
            st.write("Why it matters:", payload["answer"]["graph_value"])
            st.write("Recommended actions:")
            for action in payload["answer"]["recommended_actions"]:
                st.write(f"- {action}")
            with st.expander("Evidence"):
                for item in payload["retrieval"]["evidence"]:
                    st.write(
                        f"- {item['node']['name']} ({item['node']['kind']}) "
                        f"[score={item['score']}]"
                    )
            with st.expander("Connected paths"):
                if payload["retrieval"]["paths"]:
                    for path in payload["retrieval"]["paths"]:
                        st.write(f"- {path['narrative']}")
                else:
                    st.write("No explicit multi-hop path kept in this retrieval mode.")

    if result.get("graph"):
        st.subheader("Graph View")
        st.graphviz_chart(graphviz_for(result["graph"]), use_container_width=True)

        with st.expander("Graph retrieval details"):
            st.json(result["graph"]["retrieval"])

st.caption(f"API endpoint: {API_BASE_URL}")

