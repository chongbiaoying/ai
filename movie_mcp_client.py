import asyncio
import sys
from pathlib import Path

from mcp import (
    Client,
    StdioServerParameters,
)


async def main():

    server = StdioServerParameters(
        command=sys.executable,
        args=[
            str(Path(__file__).resolve().with_name("movie_mcp_server.py"))
        ],
    )

    async with Client(server) as client:

        # 1. 看 Server 提供了哪些工具
        tools = await client.list_tools()

        print("MCP Server 提供的工具：")

        for tool in tools.tools:
            print("-", tool.name)

        # 2. 真正调用一个工具
        result = await client.call_tool(
            "search_movies",
            {
                "keyword": "科幻"
            },
        )

        print("\n查询结果：")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
