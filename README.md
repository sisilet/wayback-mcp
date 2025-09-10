### Wayback Machine MCP Server (Python)

[![CI](https://github.com/sisilet/wayback_mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sisilet/wayback_mcp/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/wayback-mcp.svg)](https://pypi.org/project/wayback-mcp/)
[![Python versions](https://img.shields.io/pypi/pyversions/wayback-mcp.svg)](https://pypi.org/project/wayback-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Model Context Protocol (MCP) server that provides access to the Internet Archive Wayback Machine: list snapshots and fetch archived pages. Inspired by the TypeScript server described in the LobeHub listing.

- Reference: Wayback MCP (listing) — [link](https://lobehub.com/mcp/cyreslab-ai-wayback-mcp-server)
- Reference: Internet Archive APIs — [Wayback APIs index](https://archive.org/developers/index-apis.html)
- Reference: MCP server quickstart — [Build an MCP Server](https://modelcontextprotocol.io/quickstart/server)

#### Features
- Tools
  - `get_snapshots(url, from, to, limit, match_type)` via Wayback CDX API
  - `get_archived_page(url, timestamp, original)` fetches archived content
  - `search_items(query, mediatype, collection, fields, sort, rows, page)` searches archive.org items
- Resource
  - `wayback://{url}/{timestamp}` returns the archived page content

#### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Run (stdio)
```bash
python -m wayback_mcp.server
```
#### Install as CLI
```bash
pip install wayback-mcp
wayback-mcp
```

#### Run with uvx (no install)
```bash
uvx wayback-mcp
```

- Pin Python version:
```bash
uvx --python 3.12 wayback-mcp
```

- Pin package version:
```bash
uvx --from wayback-mcp==0.1.1 wayback-mcp
```


#### Configure in MCP client
Claude Desktop settings (example):
```json
{
  "mcpServers": {
    "wayback-machine": {
      "command": "wayback-mcp",
      "args": [],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Alternatively, using uvx (no install):
```json
{
  "mcpServers": {
    "wayback-machine": {
      "command": "uvx",
      "args": ["wayback-mcp"],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

#### Usage examples
- Tool call (snapshots):
```
get_snapshots(url="example.com", from="20200101", to="20201231", limit=10)
```
- Tool call (page):
```
get_archived_page(url="example.com", timestamp="20200101120000", original=true)
```
- Tool call (items search):
```
search_items(
  query="title:(Wayback) AND creator:(Internet Archive)",
  mediatype="texts",
  fields=["identifier","title","creator","mediatype","publicdate"],
  sort=["publicdate desc"],
  rows=20,
  page=1
)
```
- Resource fetch:
```
wayback://example.com/20200101120000
```

#### Notes
- Snapshot data via CDX API: `https://web.archive.org/cdx/search/cdx?url={url}&output=json`
- Page retrieval via Wayback: `https://web.archive.org/web/{timestamp}/{url}` (or `id_` mode for original content)
- Advanced item search endpoint: `https://archive.org/advancedsearch.php` (JSON output)
