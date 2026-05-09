from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    system_prompt: str = Field(min_length=1)
    model: str = ""
    tools: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    limits: dict[str, Any] = Field(default_factory=dict)
    guardrails: dict[str, Any] = Field(default_factory=dict)
    memory_settings: dict[str, Any] = Field(default_factory=dict)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools: list[str] | None = None
    channels: list[str] | None = None
    limits: dict[str, Any] | None = None
    guardrails: dict[str, Any] | None = None
    memory_settings: dict[str, Any] | None = None


class AgentRead(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class WorkflowBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    definition: dict[str, Any]


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    definition: dict[str, Any] | None = None


class WorkflowRead(WorkflowBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class RunCreate(BaseModel):
    input: str = ""
    user_id: str | None = None
    execute_async: bool = True


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    status: str
    input: str
    output: str
    state: dict[str, Any]
    token_usage: dict[str, Any]
    cost_usd: float
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    workflow_id: str
    sender_id: str
    recipient_id: str
    channel: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="meta")
    created_at: datetime


class RunEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    event_type: str
    node_id: str | None
    payload: dict[str, Any]
    created_at: datetime


class MemoryRecordCreate(BaseModel):
    agent_id: str | None = None
    workflow_id: str | None = None
    run_id: str | None = None
    user_id: str | None = None
    memory_scope: str = "workflow"
    memory_type: str = "message"
    content: str
    source_message_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryHit(BaseModel):
    id: str
    content: str
    score: float
    agent_id: str | None = None
    workflow_id: str | None = None
    run_id: str | None = None
    user_id: str | None = None
    memory_scope: str
    memory_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MemoryRecallRequest(BaseModel):
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=5, ge=1, le=50)


class TemplateRead(BaseModel):
    id: str
    name: str
    description: str


class TemplateInstantiateRequest(BaseModel):
    name: str | None = None


class ChannelConnectRequest(BaseModel):
    channel: Literal["telegram"]
    name: str = "telegram"
    bot_token: str | None = None
    default_workflow_id: str | None = None


class ChannelBindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    name: str
    config: dict[str, Any]
    default_workflow_id: str | None
    created_at: datetime


class ToolSpecRead(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolExecuteRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    name: str
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
