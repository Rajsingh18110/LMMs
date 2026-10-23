"""
DNS Enumeration & Domain Intelligence Tool for LMMs.
Provides authoritative DNS lookups (A, AAAA, CNAME, MX, TXT, NS, SOA, PTR),
wildcard detection, and evidence-classified subdomain validation.
"""

import time
import socket
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

try:
    import dns.resolver
    import dns.reversename
    import dns.exception
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

from lmms.backend.tools.core import default_registry, default_executor, ToolDefinition, Permission


class DNSEvidenceStatus:
    VERIFIED_RECORD = "VERIFIED_RECORD"
    WILDCARD_MATCH = "WILDCARD_MATCH"
    NEGATIVE_RESPONSE = "NEGATIVE_RESPONSE"
    FAILED_TIMEOUT = "FAILED_TIMEOUT"
    ERROR = "ERROR"


class DNSEnumerator:
    """
    Robust, evidence-aware DNS resolution and subdomain discovery engine.
    Ensures speculative candidates are never conflated with confirmed records.
    """

    DEFAULT_SUBDOMAIN_CANDIDATES = [
        "www", "api", "app", "dev", "docs", "mail", "blog", 
        "portal", "auth", "admin", "cdn", "status", "stage", "test"
    ]

    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout

    def _get_resolver(self):
        if not HAS_DNSPYTHON:
            return None
        resolver = dns.resolver.Resolver()
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout
        return resolver

    def query_records(self, domain: str, record_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Query standard DNS records for a given domain.
        Supported types: A, AAAA, CNAME, MX, NS, TXT, SOA.
        """
        domain = domain.strip().lower().rstrip(".")
        if not domain:
            return {"error": "Domain must not be empty.", "records": {}}

        if record_types is None:
            record_types = ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA"]

        results = {}
        resolver = self._get_resolver()

        for rtype in record_types:
            rtype = rtype.upper().strip()
            start_t = time.time()
            if resolver:
                try:
                    answers = resolver.resolve(domain, rtype)
                    records_data = []
                    for rdata in answers:
                        if rtype == "MX":
                            records_data.append({"preference": rdata.preference, "exchange": str(rdata.exchange).rstrip(".")})
                        elif rtype == "SOA":
                            records_data.append({
                                "mname": str(rdata.mname).rstrip("."),
                                "rname": str(rdata.rname).rstrip("."),
                                "serial": rdata.serial
                            })
                        else:
                            records_data.append(str(rdata).strip('"'))
                    results[rtype] = {
                        "status": DNSEvidenceStatus.VERIFIED_RECORD,
                        "records": records_data,
                        "duration_ms": round((time.time() - start_t) * 1000, 2)
                    }
                except dns.resolver.NXDOMAIN:
                    results[rtype] = {
                        "status": DNSEvidenceStatus.NEGATIVE_RESPONSE,
                        "records": [],
                        "detail": "NXDOMAIN (domain does not exist)"
                    }
                except dns.resolver.NoAnswer:
                    results[rtype] = {
                        "status": DNSEvidenceStatus.NEGATIVE_RESPONSE,
                        "records": [],
                        "detail": "NODATA (record type not present)"
                    }
                except dns.exception.Timeout:
                    results[rtype] = {
                        "status": DNSEvidenceStatus.FAILED_TIMEOUT,
                        "records": [],
                        "detail": "Resolver query timed out"
                    }
                except Exception as e:
                    results[rtype] = {
                        "status": DNSEvidenceStatus.ERROR,
                        "records": [],
                        "detail": str(e)
                    }
            else:
                # Fallback to standard library socket for A and AAAA
                if rtype == "A":
                    try:
                        addrs = socket.gethostbyname_ex(domain)[2]
                        results[rtype] = {
                            "status": DNSEvidenceStatus.VERIFIED_RECORD,
                            "records": addrs,
                            "duration_ms": round((time.time() - start_t) * 1000, 2)
                        }
                    except socket.gaierror as e:
                        results[rtype] = {
                            "status": DNSEvidenceStatus.NEGATIVE_RESPONSE,
                            "records": [],
                            "detail": str(e)
                        }
                else:
                    results[rtype] = {
                        "status": DNSEvidenceStatus.NEGATIVE_RESPONSE,
                        "records": [],
                        "detail": "Standard library fallback only supports A records without dnspython"
                    }

        return {
            "domain": domain,
            "queried_types": record_types,
            "records": results,
            "timestamp": time.time()
        }

    def check_wildcard(self, domain: str) -> Optional[List[str]]:
        """
        Check if the domain has wildcard DNS enabled by querying a random UUID subdomain.
        Returns list of IP addresses if wildcard is present, or None.
        """
        rand_prefix = "lmms-probe-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        probe_domain = f"{rand_prefix}.{domain}"

        resolver = self._get_resolver()
        if resolver:
            try:
                answers = resolver.resolve(probe_domain, "A")
                return [str(rdata) for rdata in answers]
            except Exception:
                return None
        else:
            try:
                return socket.gethostbyname_ex(probe_domain)[2]
            except Exception:
                return None

    def enumerate_subdomains(
        self,
        domain: str,
        candidates: Optional[List[str]] = None,
        max_candidates: int = 20
    ) -> Dict[str, Any]:
        """
        Perform bounded, evidence-aware subdomain validation against actual resolvers.
        Discovers active subdomains without blind HTTP probing.
        """
        domain = domain.strip().lower().rstrip(".")
        if not domain:
            return {"error": "Domain must not be empty.", "discovered": [], "summary": "Invalid domain"}

        candidate_list = list(candidates) if candidates else list(self.DEFAULT_SUBDOMAIN_CANDIDATES)
        # Limit candidate list to bounded ceiling
        candidate_list = candidate_list[:max_candidates]

        # 1. Wildcard detection
        wildcard_ips = self.check_wildcard(domain)
        has_wildcard = bool(wildcard_ips)

        discovered = []
        tested_count = 0

        def _resolve_candidate(prefix: str):
            hostname = f"{prefix}.{domain}" if not prefix.endswith(f".{domain}") and prefix != domain else prefix
            start_t = time.time()
            res_entry = {
                "hostname": hostname,
                "prefix": prefix,
                "status": DNSEvidenceStatus.NEGATIVE_RESPONSE,
                "addresses": [],
                "cnames": [],
                "duration_ms": 0
            }

            resolver = self._get_resolver()
            if resolver:
                try:
                    answers = resolver.resolve(hostname, "A")
                    ips = [str(r) for r in answers]
                    res_entry["duration_ms"] = round((time.time() - start_t) * 1000, 2)
                    res_entry["addresses"] = ips

                    # Check if ips match wildcard
                    if has_wildcard and set(ips) == set(wildcard_ips):
                        res_entry["status"] = DNSEvidenceStatus.WILDCARD_MATCH
                    else:
                        res_entry["status"] = DNSEvidenceStatus.VERIFIED_RECORD
                except dns.resolver.NXDOMAIN:
                    res_entry["status"] = DNSEvidenceStatus.NEGATIVE_RESPONSE
                except dns.resolver.NoAnswer:
                    # Might have CNAME
                    try:
                        cname_ans = resolver.resolve(hostname, "CNAME")
                        res_entry["cnames"] = [str(c.target).rstrip(".") for c in cname_ans]
                        res_entry["status"] = DNSEvidenceStatus.VERIFIED_RECORD
                    except Exception:
                        res_entry["status"] = DNSEvidenceStatus.NEGATIVE_RESPONSE
                except dns.exception.Timeout:
                    res_entry["status"] = DNSEvidenceStatus.FAILED_TIMEOUT
                except Exception:
                    res_entry["status"] = DNSEvidenceStatus.NEGATIVE_RESPONSE
            else:
                try:
                    ips = socket.gethostbyname_ex(hostname)[2]
                    res_entry["duration_ms"] = round((time.time() - start_t) * 1000, 2)
                    res_entry["addresses"] = ips
                    if has_wildcard and set(ips) == set(wildcard_ips):
                        res_entry["status"] = DNSEvidenceStatus.WILDCARD_MATCH
                    else:
                        res_entry["status"] = DNSEvidenceStatus.VERIFIED_RECORD
                except Exception:
                    res_entry["status"] = DNSEvidenceStatus.NEGATIVE_RESPONSE

            return res_entry

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_resolve_candidate, p) for p in candidate_list]
            for f in as_completed(futures):
                tested_count += 1
                entry = f.result()
                if entry["status"] in (DNSEvidenceStatus.VERIFIED_RECORD, DNSEvidenceStatus.WILDCARD_MATCH):
                    discovered.append(entry)

        # Sort discovered alphabetically
        discovered.sort(key=lambda x: x["hostname"])

        return {
            "domain": domain,
            "wildcard_detected": has_wildcard,
            "wildcard_ips": wildcard_ips or [],
            "candidates_tested": tested_count,
            "discovered_subdomains": discovered,
            "verified_count": len([d for d in discovered if d["status"] == DNSEvidenceStatus.VERIFIED_RECORD])
        }

    def reverse_lookup(self, ip_address: str) -> Dict[str, Any]:
        """Perform reverse DNS (PTR) lookup for an IP address."""
        ip_address = ip_address.strip()
        try:
            resolver = self._get_resolver()
            if resolver and HAS_DNSPYTHON:
                rev_name = dns.reversename.from_address(ip_address)
                answers = resolver.resolve(rev_name, "PTR")
                ptrs = [str(a.target).rstrip(".") for a in answers]
                return {
                    "ip": ip_address,
                    "status": DNSEvidenceStatus.VERIFIED_RECORD,
                    "ptr_records": ptrs
                }
            else:
                host, _, _ = socket.gethostbyaddr(ip_address)
                return {
                    "ip": ip_address,
                    "status": DNSEvidenceStatus.VERIFIED_RECORD,
                    "ptr_records": [host]
                }
        except Exception as e:
            return {
                "ip": ip_address,
                "status": DNSEvidenceStatus.NEGATIVE_RESPONSE,
                "ptr_records": [],
                "error": str(e)
            }


# Canonical tool function for execution
def dns_enumerate_tool(domain: str, query_type: str = "all", candidates: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Main entry point for DNS enumeration and domain intelligence.
    query_type: 'records' | 'subdomains' | 'all'
    """
    enumerator = DNSEnumerator(timeout=2.5)
    result = {"domain": domain, "query_type": query_type}

    if query_type in ("records", "all"):
        result["dns_records"] = enumerator.query_records(domain)

    if query_type in ("subdomains", "all"):
        result["subdomain_discovery"] = enumerator.enumerate_subdomains(domain, candidates=candidates)

    return result


def format_dns_tool_output(data: Dict[str, Any]) -> str:
    """Format structured DNS data into a clean, human and LLM-readable observation string."""
    domain = data.get("domain", "")
    lines = [f"=== DNS & DOMAIN INTELLIGENCE: {domain} ==="]

    if "dns_records" in data:
        rec_data = data["dns_records"].get("records", {})
        lines.append("\n[Authoritative DNS Records]:")
        found_any = False
        for rtype, rinfo in rec_data.items():
            if rinfo.get("status") == DNSEvidenceStatus.VERIFIED_RECORD:
                records = rinfo.get("records", [])
                if records:
                    found_any = True
                    rec_strs = []
                    for r in records:
                        if isinstance(r, dict):
                            rec_strs.append(", ".join(f"{k}={v}" for k, v in r.items()))
                        else:
                            rec_strs.append(str(r))
                    lines.append(f"  • {rtype:5s}: {'; '.join(rec_strs)}")
        if not found_any:
            lines.append("  (No standard public A/MX/NS records resolved or negative response)")

    if "subdomain_discovery" in data:
        sub_data = data["subdomain_discovery"]
        wildcard = sub_data.get("wildcard_detected", False)
        tested = sub_data.get("candidates_tested", 0)
        verified = sub_data.get("verified_count", 0)
        discovered = sub_data.get("discovered_subdomains", [])

        lines.append(f"\n[Subdomain Enumeration] (Tested: {tested} candidates, Wildcard: {'YES' if wildcard else 'NO'}):")
        if not discovered:
            lines.append(f"  • 0 active subdomains discovered among tested candidates for {domain}.")
            lines.append("  • Evidence Note: Negative responses indicate queried hostnames do not resolve.")
        else:
            for d in discovered:
                status_badge = "VERIFIED" if d["status"] == DNSEvidenceStatus.VERIFIED_RECORD else "WILDCARD_MATCH"
                addrs = ", ".join(d.get("addresses", [])) or "CNAME: " + ", ".join(d.get("cnames", []))
                lines.append(f"  • [{status_badge}] {d['hostname']} -> {addrs}")

    return "\n".join(lines)


# Register in canonical ToolDefinition registry
default_registry.register(ToolDefinition(
    name="dns.enumerate",
    description="Discover and verify DNS records (A, AAAA, MX, NS, TXT, SOA) and validate active subdomains using authoritative DNS resolvers. Avoids blind HTTP probing.",
    category="network",
    parameters={"domain": "str", "query_type": "str", "candidates": "list"},
    permissions=[Permission.WEB_SEARCH],
    risk_level="low",
    requires_network=True,
    callback=dns_enumerate_tool
))

# Convenience alias for model function calling
def dns_enumerate(domain: str, query_type: str = "all", candidates: Optional[List[str]] = None) -> str:
    """Wrapper that returns formatted evidence string for the agent."""
    res = dns_enumerate_tool(domain, query_type=query_type, candidates=candidates)
    return format_dns_tool_output(res)
