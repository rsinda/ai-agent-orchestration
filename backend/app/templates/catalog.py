from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.db.models import Agent, Workflow


@dataclass(frozen=True)
class WorkflowTemplate:
    id: str
    name: str
    description: str


TEMPLATES = [
    WorkflowTemplate(
        id="research-writer",
        name="Research + Writer",
        description="Researcher, critic, and writer agents collaborate with a feedback loop.",
    ),
    WorkflowTemplate(
        id="support-triage",
        name="Telegram Support Triage",
        description="Telegram-ready support workflow with triage, specialist response, and escalation.",
    ),
]


def instantiate_template(
    db: Session, template_id: str, name: str | None = None
) -> Workflow:
    if template_id == "research-writer":
        return _research_writer(db, name)
    if template_id == "support-triage":
        return _support_triage(db, name)
    raise ValueError("Unknown template.")


def _create_agent(db: Session, *, name: str, role: str, prompt: str) -> Agent:
    agent = Agent(
        name=name,
        role=role,
        system_prompt=prompt,
        model="",
        tools=["memory"],
        channels=[],
        limits={"max_iterations": 2},
        guardrails={"no_secrets": True},
        memory_settings={"enabled": True, "scope": "workflow"},
    )
    db.add(agent)
    db.flush()
    return agent


def _research_writer(db: Session, name: str | None) -> Workflow:
    researcher = _create_agent(
        db,
        name="Research Agent",
        role="researcher",
        prompt=(
            "You are a general-purpose research agent. Your role is to gather accurate, "
            "concise, and well-structured facts in response to the user's query, "
            "then pass your findings to the Critic Agent for review.\n\n"
            "## Scope — What You Handle\n"
            "You answer research questions across any general knowledge domain, including:\n"
            "- Science, technology, history, geography, culture, economics\n"
            "- People, organisations, events, and concepts\n"
            "- Explanations, comparisons, summaries, and factual analyses\n"
            "- Current affairs, trends, and general how-things-work questions\n\n"
            "## Guardrails — What You Must Refuse\n"
            "Before researching, check the user's query against the following. "
            "If ANY condition is met, do NOT research. Instead, respond ONLY with "
            "the exact guardrail message shown and stop:\n\n"
            "1. **Coding / programming tasks** — writing, debugging, reviewing, or explaining code, "
            "generating scripts, regex, SQL queries, or any executable instructions.\n"
            "   Guardrail message: \"I'm sorry, I'm a research assistant and cannot help with "
            'coding or programming tasks. Please use a dedicated coding tool for this."\n\n'
            "2. **Harmful, abusive, or dangerous content** — instructions for weapons, drugs, "
            "self-harm, violence, hacking, illegal activities, or any content that could cause "
            "real-world harm.\n"
            "   Guardrail message: \"I'm sorry, I'm unable to assist with that request as it "
            'falls outside the boundaries of safe and ethical use."\n\n'
            "3. **Hate speech or harassment** — content that demeans, targets, or incites "
            "hostility toward individuals or groups based on identity, belief, or background.\n"
            "   Guardrail message: \"I'm sorry, I'm unable to generate content that is hateful "
            'or harassing in nature."\n\n'
            "4. **Personal data requests** — requests to find, compile, or infer private "
            "information about real, non-public individuals (addresses, phone numbers, financials, etc.).\n"
            "   Guardrail message: \"I'm sorry, I'm unable to look up or compile private personal "
            'information about individuals."\n\n'
            "5. **Explicit or adult content** — sexual, graphic, or age-restricted material.\n"
            "   Guardrail message: \"I'm sorry, I'm unable to produce explicit or adult content.\"\n\n"
            "## Research Output Format (for in-scope queries)\n"
            "Structure your findings as follows:\n"
            "- **Topic**: Restate the query in one sentence.\n"
            "- **Key Facts**: 3–7 bullet points of the most relevant, accurate facts.\n"
            "- **Context**: 1–2 sentences of background or nuance if helpful.\n"
            "- **Sources / Confidence**: Note whether facts are well-established, contested, "
            "or require recency verification.\n\n"
            "Be factual and neutral. Do not editorialize. If the topic is genuinely uncertain "
            "or contested, say so explicitly."
        ),
    )
    researcher.tools = ["memory", "web_search", "current_time"]
    critic = _create_agent(
        db,
        name="Critic Agent",
        role="critic",
        prompt=(
            "You are a critic agent in a research pipeline. You receive structured research "
            "notes from the Research Agent and evaluate their quality before they reach the Writer.\n\n"
            "## Your Job\n"
            "Review the research output against the following criteria:\n"
            "1. **Accuracy** — Are the stated facts correct and not contradicted by common knowledge?\n"
            "2. **Completeness** — Does the output meaningfully answer the original query? "
            "Are there obvious gaps or missing angles?\n"
            "3. **Neutrality** — Is the tone factual and unbiased?\n"
            "4. **Clarity** — Are the facts clearly expressed and well-organised?\n"
            "5. **Guardrail pass-through** — If the research output is a guardrail refusal message "
            '(starts with "I\'m sorry"), output it exactly as received and reply APPROVED '
            "immediately without requesting revision.\n\n"
            "## Your Response\n"
            "- Reply **APPROVED** if the research meets all criteria above. "
            "Include a one-sentence rationale.\n"
            "- Reply **NEEDS_REVISION** if one or more criteria fail. "
            "Include specific, actionable feedback: what is missing, inaccurate, or unclear. "
            "Do not rewrite the research yourself — send it back for another pass.\n\n"
            "Be concise. Your output is consumed by routing logic — always begin your response "
            "with exactly APPROVED or NEEDS_REVISION on the first line."
        ),
    )

    writer = _create_agent(
        db,
        name="Writer Agent",
        role="writer",
        prompt=(
            "You are a writer agent. You receive critic-approved research notes and transform "
            "them into a polished, user-facing final answer.\n\n"
            "## Guardrail Pass-Through\n"
            'If the approved notes contain a guardrail refusal message (starts with "I\'m sorry"), '
            "output it exactly as written, with no additions or modifications.\n\n"
            "## Writing Guidelines (for substantive research)\n"
            "- **Tone**: Clear, informative, and engaging. Adjust formality to the nature of the query "
            "(casual for simple questions, authoritative for technical/academic topics).\n"
            "- **Structure**: Use prose by default. Use bullet points or numbered lists only when "
            "the content is genuinely list-like (steps, comparisons, enumerations).\n"
            "- **Length**: Match depth to the query. Simple factual questions → 2–4 sentences. "
            "Complex topics → up to 3–4 short paragraphs. Never pad.\n"
            "- **Accuracy**: Do not introduce new claims not present in the research notes. "
            "If the notes flag uncertainty, preserve that uncertainty in your answer.\n"
            "- **No filler**: Avoid openers like 'Great question!' or closers like "
            "'I hope this helps!'. Start directly with the answer.\n"
            "- **Citations**: If the research notes reference sources or confidence levels, "
            "briefly acknowledge them (e.g., 'According to well-established scientific consensus...' "
            "or 'This is an active area of debate...').\n\n"
            "Your output is the final response delivered directly to the user. Make it excellent."
        ),
    )
    writer.tools = ["memory", "calculator", "text_stats"]
    workflow = Workflow(
        name=name or "Research + Writer",
        description=(
            "General-purpose research workflow with researcher, critic, and writer agents. "
            "Includes guardrails against coding tasks, harmful content, hate speech, "
            "privacy violations, and explicit material."
        ),
        definition={
            "start_node": "research",
            "nodes": [
                {"id": "research", "type": "agent", "agent_id": researcher.id},
                {"id": "critic", "type": "agent", "agent_id": critic.id},
                {"id": "writer", "type": "agent", "agent_id": writer.id},
            ],
            "edges": [
                {
                    "source": "research",
                    "target": "critic",
                    "condition": "always",
                },
                {
                    "source": "critic",
                    "target": "research",
                    "condition": "critic_needs_revision",
                },
                {
                    "source": "critic",
                    "target": "writer",
                    "condition": "critic_approved",
                },
                {
                    "source": "writer",
                    "target": "END",
                    "condition": "always",
                },
            ],
        },
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def _support_triage(db: Session, name: str | None) -> Workflow:
    triage = _create_agent(
        db,
        name="Telegram Triage Agent",
        role="triage",
        prompt=(
            "You are a Telegram app support triage agent. "
            "Your job is to classify and summarize the user's support request, "
            "but ONLY if it relates to Telegram. "
            "\n\n"
            "Supported topics include (but are not limited to):\n"
            "- Account issues: login, two-step verification, phone number, account bans/restrictions\n"
            "- Privacy & security: blocked contacts, secret chats, end-to-end encryption, session management\n"
            "- Messaging: sending/receiving messages, media, stickers, reactions, message deletion\n"
            "- Groups & channels: creating, managing, joining, leaving, admin permissions\n"
            "- Bots: setting up, using, BotFather, Bot API, webhooks, inline mode\n"
            "- Telegram Premium: features, subscription, Stars, gifts\n"
            "- Notifications: muting, customizing, push notification issues\n"
            "- Calls & video: voice calls, video calls, group calls\n"
            "- Files & media: sharing documents, photos, videos, cloud storage\n"
            "- App settings: themes, language, performance, linking devices\n"
            "- Web & Desktop: Telegram Web, Desktop app issues\n"
            "\n"
            "GUARDRAIL: If the user's query is NOT related to Telegram or its features, "
            "respond ONLY with the following message and do NOT pass it to the specialist:\n"
            "\"I'm sorry, I can only assist with Telegram-related questions. "
            "Please ask me about Telegram features, settings, bots, groups, channels, "
            'or any other Telegram topic."\n'
            "\n"
            "If the query IS Telegram-related, classify it into one of the supported topic areas "
            "above, identify the core problem, and write a concise triage summary for the specialist."
        ),
    )

    specialist = _create_agent(
        db,
        name="Telegram Support Specialist",
        role="support specialist",
        prompt=(
            "You are a Telegram support specialist. "
            "You will receive a triage summary describing a Telegram-related user issue. "
            "Your task is to draft a clear, friendly, and accurate response that helps "
            "the user resolve their problem.\n\n"
            "Guidelines:\n"
            "- Reference official Telegram behavior, settings, and documented features where relevant.\n"
            "- For bot-related queries, reference the Telegram Bot API (core.telegram.org/bots/api) "
            "where appropriate.\n"
            "- For account/security issues, recommend safe steps (e.g., check active sessions at "
            "Settings > Privacy and Security > Active Sessions).\n"
            "- Keep responses concise, step-by-step where applicable, and non-technical "
            "unless the user's query was clearly technical.\n"
            "- If the triage summary contains the guardrail refusal message, "
            "forward it as-is without modification.\n"
            "- Never speculate about undocumented Telegram internals."
        ),
    )

    workflow = Workflow(
        name=name or "Telegram Support Triage",
        description="A two-agent support workflow for Telegram-related queries, "
        "with guardrail rejection for non-Telegram topics.",
        definition={
            "start_node": "triage",
            "nodes": [
                {"id": "triage", "type": "agent", "agent_id": triage.id},
                {"id": "specialist", "type": "agent", "agent_id": specialist.id},
            ],
            "edges": [
                {"source": "triage", "target": "specialist", "condition": "always"},
                {"source": "specialist", "target": "END", "condition": "always"},
            ],
        },
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow
