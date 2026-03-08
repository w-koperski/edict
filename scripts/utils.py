#!/usr/bin/env python3
"""
Three Departments & Six Ministries · Common utility functions
Avoids repeated definitions of read_json / now_iso and other basic helpers across scripts
"""
import json, pathlib, datetime


def read_json(path, default=None):
    """Safely read a JSON file, returns default on failure"""
    try:
        return json.loads(pathlib.Path(path).read_text())
    except Exception:
        return default if default is not None else {}


def now_iso():
    """Return UTC ISO 8601 timestamp string (trailing Z)"""
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def today_str(fmt='%Y%m%d'):
    """Return today's date string, default format YYYYMMDD"""
    return datetime.date.today().strftime(fmt)


def safe_name(s: str) -> bool:
    """Check if a name contains only safe characters (letters, digits, underscore, hyphen, CJK)"""
    import re
    return bool(re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fff]+$', s))


def validate_url(url: str, allowed_schemes=('https',), allowed_domains=None) -> bool:
    """Validate URL safety, prevent SSRF"""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            return False
        if allowed_domains and parsed.hostname not in allowed_domains:
            return False
        if not parsed.hostname:
            return False
        # Block private/internal addresses
        import ipaddress
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                return False
        except ValueError:
            pass  # hostname is not an IP, allow through
        return True
    except Exception:
        return False
