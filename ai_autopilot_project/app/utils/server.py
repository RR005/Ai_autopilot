from fastmcp import FastMCP
from mcp.server.fastmcp import Context
import json
import nest_asyncio
nest_asyncio.apply()

mcp = FastMCP("WriterAgentApp")

@mcp.tool()
async def prune_context(
    task: str,
    diagnosis: dict,
    script_code: str,
    ctx: Context
) -> str:
    ctx.info("Pruning context for task")  # optional logging
    chunks = []
    if diagnosis:
        chunks.append("Diagnosis: " + json.dumps(diagnosis))
    if script_code:
        chunks.append("Script:\n" + script_code)
    response = await ctx.llm(
        messages=[
            {"role": "system", "content": "Select relevant context chunks."},
            {"role": "user", "content": "\n\n".join(chunks)},
        ],
        max_tokens=400
    )
    return response.content.strip()
