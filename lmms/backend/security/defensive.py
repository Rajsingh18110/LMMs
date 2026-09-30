import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List

def get_evidence_dir(workspace: str) -> str:
    path = os.path.join(workspace, ".lmms", "evidence")
    os.makedirs(path, exist_ok=True)
    return path

def record_evidence(workspace: str, command: str, target: str, result_summary: str):
    """Save structured logs of actions into .lmms/evidence/timeline.jsonl."""
    if not workspace or workspace == "None":
        return
        
    ev_dir = get_evidence_dir(workspace)
    timeline_path = os.path.join(ev_dir, "timeline.jsonl")
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "target": target,
        "result": result_summary
    }
    
    with open(timeline_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

def parse_nmap(xml_file_path: str) -> List[Dict[str, Any]]:
    """Parse Nmap XML and normalize findings (open ports, services)."""
    # Simple regex fallback if xml.etree is too complex for basic needs
    # but let's use xml.etree since it's standard
    import xml.etree.ElementTree as ET
    
    if not os.path.exists(xml_file_path):
        return []
        
    findings = []
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        for host in root.findall("host"):
            ip = ""
            for addr in host.findall("address"):
                if addr.get("addrtype") == "ipv4":
                    ip = addr.get("addr")
                    
            if not ip:
                continue
                
            ports = host.find("ports")
            if ports is not None:
                for port in ports.findall("port"):
                    state_elem = port.find("state")
                    state = state_elem.get("state") if state_elem is not None else "unknown"
                    
                    if state == "open":
                        port_id = port.get("portid")
                        protocol = port.get("protocol")
                        
                        service_elem = port.find("service")
                        service_name = service_elem.get("name") if service_elem is not None else "unknown"
                        
                        findings.append({
                            "ip": ip,
                            "port": port_id,
                            "protocol": protocol,
                            "service": service_name,
                            "state": state
                        })
    except Exception:
        pass
        
    return findings

def parse_logs(log_file_path: str, log_type: str = "auth") -> List[Dict[str, Any]]:
    """Simple regex/parsing for auth.log or access logs."""
    if not os.path.exists(log_file_path):
        return []
        
    results = []
    try:
        with open(log_file_path, "r") as f:
            for line in f:
                line = line.strip()
                if log_type == "auth" and "Failed password" in line:
                    results.append({"type": "failed_login", "raw": line})
                elif log_type == "access" and " 404 " in line:
                    results.append({"type": "404_not_found", "raw": line})
    except Exception:
        pass
        
    return results

def build_inventory(workspace: str, new_findings: List[Dict[str, Any]]):
    """Compile discovered assets into an asset_inventory.json."""
    if not workspace or workspace == "None":
        return
        
    ev_dir = get_evidence_dir(workspace)
    inv_path = os.path.join(ev_dir, "asset_inventory.json")
    
    inventory = []
    if os.path.exists(inv_path):
        try:
            with open(inv_path, "r") as f:
                inventory = json.load(f)
        except Exception:
            inventory = []
            
    # Add new findings avoiding strict duplicates
    for finding in new_findings:
        if finding not in inventory:
            inventory.append(finding)
            
    with open(inv_path, "w") as f:
        json.dump(inventory, f, indent=2)
