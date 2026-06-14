import httpx
from ..base import ToolResult

async def execute_cve_lookup(params: dict) -> ToolResult:
    cve_id = params.get("cve_id")
    if not cve_id:
        return ToolResult(tool_name="cve_lookup", success=False, data=None, error="Missing cve_id")
    
    # Needs to match CVE-YYYY-NNNNN format
    if not cve_id.upper().startswith("CVE-"):
        cve_id = f"CVE-{cve_id}"
        
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id.upper()}")
            if r.status_code == 200:
                data = r.json()
                vulnerabilities = data.get("vulnerabilities", [])
                if not vulnerabilities:
                    return ToolResult(tool_name="cve_lookup", success=True, data={"error": "CVE not found"})
                cve = vulnerabilities[0].get("cve", {})
                desc = next((d.get("value") for d in cve.get("descriptions", []) if d.get("lang") == "en"), "")
                metrics = cve.get("metrics", {})
                cvss = None
                if "cvssMetricV31" in metrics:
                    cvss = metrics["cvssMetricV31"][0].get("cvssData", {}).get("baseScore")
                
                return ToolResult(tool_name="cve_lookup", success=True, data={
                    "id": cve.get("id"),
                    "description": desc,
                    "cvss_v31_score": cvss,
                    "published": cve.get("published")
                })
            return ToolResult(tool_name="cve_lookup", success=False, data=None, error=f"Status: {r.status_code}")
        except Exception as e:
            return ToolResult(tool_name="cve_lookup", success=False, data=None, error=str(e))

async def execute_security_news(params: dict) -> ToolResult:
    limit = params.get("limit", 5)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # HackerNews top stories
            r = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            if r.status_code != 200:
                return ToolResult(tool_name="security_news", success=False, data=None, error="Failed to get stories")
                
            story_ids = r.json()[:int(limit)]
            stories = []
            for sid in story_ids:
                sr = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                if sr.status_code == 200:
                    data = sr.json()
                    # simplistic filter for security news
                    title = data.get("title", "").lower()
                    stories.append({
                        "title": data.get("title"),
                        "url": data.get("url")
                    })
            return ToolResult(tool_name="security_news", success=True, data=stories)
        except Exception as e:
            return ToolResult(tool_name="security_news", success=False, data=None, error=str(e))
