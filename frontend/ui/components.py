import json
from typing import Any

import pandas as pd
import streamlit as st


def configure_page(title: str) -> None:
    st.set_page_config(page_title=title, page_icon="AI", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.8rem; padding-bottom: 2rem;}
        div[data-testid="stMetric"] {border: 1px solid #e5e7eb; border-radius: 8px; padding: 0.75rem;}
        code {white-space: pre-wrap;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_guard(fn, fallback=None):
    try:
        return fn()
    except Exception as exc:
        st.error(str(exc))
        return fallback


def status_badge(status: str) -> None:
    color = {
        "succeeded": "green",
        "running": "blue",
        "pending": "orange",
        "failed": "red",
        "ok": "green",
    }.get((status or "").lower(), "gray")
    st.markdown(f":{color}[**{status or 'unknown'}**]")


def json_editor(label: str, value: Any, key: str, height: int = 180):
    raw = st.text_area(label, json.dumps(value or {}, indent=2), key=key, height=height)
    try:
        return json.loads(raw or "{}"), None
    except json.JSONDecodeError as exc:
        return None, exc


def dataframe(items: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if not items:
        st.info("No records yet.")
        return
    frame = pd.DataFrame(items)
    if columns:
        existing = [column for column in columns if column in frame.columns]
        frame = frame[existing]
    st.dataframe(frame, use_container_width=True, hide_index=True)


def workflow_label(workflow: dict[str, Any]) -> str:
    return f"{workflow.get('name', 'Untitled')} · {workflow.get('id', '')[:8]}"


def agent_label(agent: dict[str, Any]) -> str:
    model = agent.get("model") or "default Gemini"
    return f"{agent.get('name', 'Untitled')} · {agent.get('role', 'agent')} · {model}"

