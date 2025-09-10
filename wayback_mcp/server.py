import asyncio
from typing import Literal, Optional, Dict, Any, List

import httpx
from . import __version__

try:
	# FastMCP provides convenient decorators for tools/resources
	from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
	# Fallback import name (older package variants)
	from mcp.server.fastmcp import FastMCP  # type: ignore


USER_AGENT = f"wayback-mcp-python/{__version__} (+https://archive.org/developers/index-apis.html)"
CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
WAYBACK_ENDPOINT = "https://web.archive.org/web"
ADVANCED_SEARCH_ENDPOINT = "https://archive.org/advancedsearch.php"

app = FastMCP("wayback-machine")


def _build_cdx_params(
	url: str,
	from_date: Optional[str],
	to_date: Optional[str],
	limit: int,
	match_type: Literal["exact", "prefix", "host", "domain"],
) -> Dict[str, Any]:
	params: Dict[str, Any] = {
		"url": url,
		"output": "json",
		"limit": str(limit),
		"matchType": match_type,
		# Clean results a bit:
		"filter": "statuscode:200",
		"collapse": "digest",
	}
	if from_date:
		params["from"] = from_date
	if to_date:
		params["to"] = to_date
	return params


async def _fetch_json(url: str, params: Dict[str, Any]) -> Any:
	async with httpx.AsyncClient(
		headers={"User-Agent": USER_AGENT},
		timeout=httpx.Timeout(20.0),
		follow_redirects=True,
	) as client:
		resp = await client.get(url, params=params)
		resp.raise_for_status()
		return resp.json()


async def _fetch_text(url: str) -> httpx.Response:
	async with httpx.AsyncClient(
		headers={"User-Agent": USER_AGENT},
		timeout=httpx.Timeout(30.0),
		follow_redirects=True,
	) as client:
		resp = await client.get(url)
		# Do not raise for status here; some archived pages return non-200
		return resp


@app.tool(
	name="get_snapshots",
	description=(
		"Get a list of available Wayback Machine snapshots for a URL. "
		"Dates use YYYYMMDD, match_type is one of: exact, prefix, host, domain."
	),
)
async def get_snapshots(
	url: str,
	from_: Optional[str] = None,
	to: Optional[str] = None,
	limit: int = 100,
	match_type: Literal["exact", "prefix", "host", "domain"] = "exact",
) -> Dict[str, Any]:
	"""
	List snapshots using the CDX API. Returns a structured result with a normalized list.
	Parameter `from_` maps to `from` in the CDX API.
	"""
	params = _build_cdx_params(url, from_, to, limit, match_type)
	raw = await _fetch_json(CDX_ENDPOINT, params)

	if not isinstance(raw, list) or not raw:
		return {"url": url, "snapshots": [], "count": 0}

	headers = raw[0]
	rows = raw[1:]

	# Expected headers from CDX: urlkey,timestamp,original,mimetype,statuscode,digest,length
	index_by_name = {name: idx for idx, name in enumerate(headers)}

	results: List[Dict[str, Any]] = []
	for row in rows:
		try:
			ts = row[index_by_name.get("timestamp", 1)]
			orig = row[index_by_name.get("original", 2)]
			mime = row[index_by_name.get("mimetype", 3)]
			status = row[index_by_name.get("statuscode", 4)]
			digest = row[index_by_name.get("digest", 5)]
			length = row[index_by_name.get("length", 6)]
			archived_url = f"{WAYBACK_ENDPOINT}/{ts}/{orig}"
			results.append(
				{
					"timestamp": ts,
					"original_url": orig,
					"mimetype": mime,
					"statuscode": status,
					"digest": digest,
					"length": length,
					"archived_url": archived_url,
				}
			)
		except Exception:
			# Skip malformed rows
			continue

	return {"url": url, "snapshots": results, "count": len(results)}


@app.tool(
	name="get_archived_page",
	description=(
		"Retrieve content of an archived webpage from the Wayback Machine "
		"using YYYYMMDDHHMMSS timestamp. If original=true, request id_ mode."
	),
)
async def get_archived_page(
	url: str,
	timestamp: str,
	original: bool = False,
) -> Dict[str, Any]:
	"""
	Fetch the archived page content. Returns status, headers, and text content.
	If `original` is True, uses the `id_` mode to minimize Wayback rewriting/banners.
	"""
	mode = "id_/" if original else ""
	archived_url = f"{WAYBACK_ENDPOINT}/{timestamp}/{mode}{url}"
	resp = await _fetch_text(archived_url)

	text: Optional[str]
	try:
		text = resp.text
	except Exception:
		text = None

	return {
		"url": url,
		"timestamp": timestamp,
		"archived_url": archived_url,
		"status_code": resp.status_code,
		"headers": dict(resp.headers),
		"text": text,
	}


@app.resource("wayback://{url}/{timestamp}")
async def wayback_resource(url: str, timestamp: str):
	"""
	Resource template to fetch an archived page's content.
	Returns a single text/html content block.
	"""
	archived_url = f"{WAYBACK_ENDPOINT}/{timestamp}/{url}"
	resp = await _fetch_text(archived_url)
	mime = resp.headers.get("content-type", "text/html")
	# Some archived resources might be non-HTML; return as-is in text when decodable
	content_text: Optional[str]
	try:
		content_text = resp.text
	except Exception:
		content_text = None

	return [
		{
			"uri": archived_url,
			"mimeType": mime,
			"text": content_text,
		}
	]


@app.tool(
	name="search_items",
	description=(
		"Search Internet Archive items using Advanced Search (archive.org). "
		"Supports basic query, optional mediatype/collection filters, fields, sort, rows, and page."
	),
)
async def search_items(
	query: str,
	mediatype: Optional[str] = None,
	collection: Optional[str] = None,
	fields: Optional[List[str]] = None,
	sort: Optional[List[str]] = None,
	rows: int = 50,
	page: int = 1,
) -> Dict[str, Any]:
	"""
	Search archive.org items. Returns total, page info, and docs.
	- query: Lucene-like search string
	- mediatype: optional filter (e.g., texts, movies, audio, software, image)
	- collection: optional collection filter (e.g., web)
	- fields: list of field names to include (defaults to common ones)
	- sort: list like ["downloads desc", "publicdate desc"]
	"""
	q = query.strip() if query else "*:*"
	if mediatype:
		q += f" AND mediatype:{mediatype}"
	if collection:
		q += f" AND collection:{collection}"

	default_fields = [
		"identifier",
		"title",
		"mediatype",
		"publicdate",
		"downloads",
	]
	fl = fields if fields else default_fields

	default_sort = ["downloads desc"]
	srt = sort if sort else default_sort

	params: Dict[str, Any] = {
		"q": q,
		"fl[]": fl,
		"sort[]": srt,
		"rows": rows,
		"page": page,
		"output": "json",
	}

	data = await _fetch_json(ADVANCED_SEARCH_ENDPOINT, params)
	response = data.get("response", {}) if isinstance(data, dict) else {}
	return {
		"q": q,
		"rows": rows,
		"page": page,
		"numFound": response.get("numFound", 0),
		"docs": response.get("docs", []),
	}


def main() -> None:
	"""
	Entry point for running the MCP server over stdio.
	"""
	app.run()


if __name__ == "__main__":
	main()
