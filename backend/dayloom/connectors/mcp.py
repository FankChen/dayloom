import asyncio
import json
import re
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
from jsonschema import Draft202012Validator
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from dayloom.registry import connectors


@connectors.register
class McpDevice:
    @asynccontextmanager
    async def session(self, endpoint, token):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with httpx.AsyncClient(
            headers=headers, timeout=httpx.Timeout(75, connect=5), follow_redirects=False
        ) as http_client:
            async with streamable_http_client(endpoint, http_client=http_client) as (
                reader,
                writer,
                _session_id,
            ):
                async with ClientSession(
                    reader, writer, read_timeout_seconds=timedelta(seconds=75)
                ) as session:
                    async with asyncio.timeout(10):
                        await session.initialize()
                    yield session

    async def describe(self, endpoint, token):
        async with self.session(endpoint, token) as session:
            async with asyncio.timeout(10):
                result = await session.list_tools()
            catalog = {}
            for tool in result.tools[:50]:
                if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", tool.name):
                    continue
                schema = tool.inputSchema
                if len(json.dumps(schema)) > 4000:
                    continue
                Draft202012Validator.check_schema(schema)
                if tool.name in catalog:
                    raise ValueError("Duplicate remote tool definition")
                catalog[tool.name] = {
                    "name": tool.name,
                    "description": (tool.description or "")[:1000],
                    "input_schema": schema,
                }
            return catalog

    async def invoke(
        self, endpoint, token, name, arguments, expected_schema, action_id, authorize, state
    ):
        async with self.session(endpoint, token) as session:
            async with asyncio.timeout(10):
                listed = await session.list_tools()
            current = next((tool for tool in listed.tools[:50] if tool.name == name), None)
            if current is None or current.inputSchema != expected_schema:
                return {"blocked": True}
            authorize()
            state["attempted"] = True
            result = await session.call_tool(
                name,
                arguments,
                read_timeout_seconds=timedelta(seconds=60),
                meta={"io.dayloom/action_id": action_id},
            )
            text = "\n".join(item.text for item in result.content if item.type == "text")[:16000]
            structured = result.structuredContent
            if structured is not None and len(json.dumps(structured)) > 16000:
                structured = {"truncated": True}
            return {"blocked": False, "is_error": result.isError, "text": text, "data": structured}
