from fastapi import APIRouter, HTTPException

from backend.app.schemas import ToolExecuteRequest, ToolExecuteResponse, ToolSpecRead
from backend.app.tools.registry import default_tool_registry

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolSpecRead])
def list_tools() -> list[ToolSpecRead]:
    return [
        ToolSpecRead(
            name=spec.name,
            description=spec.description,
            input_schema=spec.input_schema,
        )
        for spec in default_tool_registry.specs()
    ]


@router.post("/{tool_name}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    tool_name: str, payload: ToolExecuteRequest
) -> ToolExecuteResponse:
    try:
        result = await default_tool_registry.execute(tool_name, payload.arguments)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ToolExecuteResponse(name=tool_name, content=result.content, data=result.data)
