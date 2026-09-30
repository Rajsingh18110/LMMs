import ipaddress
import re

def is_valid_ip_or_cidr(value: str) -> bool:
    try:
        ipaddress.ip_network(value, strict=False)
        return True
    except ValueError:
        return False

def domain_matches(target_domain: str, authorized_domain: str) -> bool:
    target_domain = target_domain.lower()
    authorized_domain = authorized_domain.lower()
    
    if target_domain == authorized_domain:
        return True
        
    if authorized_domain.startswith("*."):
        base = authorized_domain[2:]
        if target_domain == base or target_domain.endswith("." + base):
            return True
            
    return False

def is_target_authorized(target: str, authorized_targets: list) -> bool:
    # Allow local access unless explicitly overridden later? 
    # The spec says "Do not assume localhost is allowed unless explicitly authorized" 
    # But wait, it said: "Protect against accidental access to localhost... unless explicitly authorized by scope."
    # So we strictly check authorized_targets.
    
    # Strip URL structures if present to extract host
    if "://" in target:
        target = target.split("://")[1]
    target = target.split("/")[0]
    target = target.split(":")[0]

    for auth in authorized_targets:
        # Check domain match first
        if domain_matches(target, auth):
            return True
            
        # Try IP matching
        try:
            target_ip = ipaddress.ip_address(target)
            try:
                auth_network = ipaddress.ip_network(auth, strict=False)
                if target_ip in auth_network:
                    return True
            except ValueError:
                pass
        except ValueError:
            # Target is not an IP, and didn't match domain.
            pass
            
    return False
