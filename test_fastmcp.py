import asyncio
import os
from fastmcp import Client

config = {
    "mcpServers": {
        "parallel": {
            "command": "npx.cmd" if os.name == 'nt' else "npx",
            "args": ["-y", "@modelcontextprotocol/server-parallel-search"]
        }
    }
}

async def main():
    async with Client(config) as client:
        tools = await client.list_tools()
        print(f"Tools: {tools}")
        
        # Test calling the tool to see what it returns
        # res = await client.call_tool("parallel_parallel_search", arguments={"query": "test"})
        # print(res)

if __name__ == '__main__':
    asyncio.run(main())
