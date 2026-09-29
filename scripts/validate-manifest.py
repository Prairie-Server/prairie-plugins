#!/usr/bin/env python3
"""Validate the published plugin catalog (manifest.json) without network access.

Checks that the file parses and that every entry's download URLs are
well-formed: https GitHub release-asset URLs in the entry's own repository,
under the tag for the entry's version, with one binary per supported platform.
It does not fetch anything, so it cannot tell whether a release really exists.

Usage: scripts/validate-manifest.py [manifest.json]
"""
import json
import re
import sys
from urllib.parse import urlsplit

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
PLATFORM = re.compile(r"^[a-z0-9]+/[a-z0-9]+$")
REPO_PATH = re.compile(r"^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")
ASSET_PATH = re.compile(r"^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/releases/download/([^/]+)/([^/]+)$")


def check_url(value, where, errors):
    """Return the parsed URL if value is an absolute https URL, else record an error."""
    if not isinstance(value, str) or not value:
        errors.append(f"{where}: missing or not a string")
        return None
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc:
        errors.append(f"{where}: not an absolute https URL: {value!r}")
        return None
    if parts.username or parts.password or parts.query or parts.fragment or any(c.isspace() for c in value):
        errors.append(f"{where}: must not carry credentials, a query, a fragment, or whitespace: {value!r}")
        return None
    return parts


def check_asset(value, where, repo, tag, filename, errors):
    parts = check_url(value, where, errors)
    if parts is None:
        return
    m = ASSET_PATH.match(parts.path)
    if parts.netloc != "github.com" or not m:
        errors.append(f"{where}: not a GitHub release-asset URL: {value!r}")
        return
    owner, name, url_tag, url_file = m.groups()
    if repo and (owner.lower(), name.lower()) != repo:
        errors.append(f"{where}: points at {owner}/{name}, but repo_url is {'/'.join(repo)}")
    if url_tag != tag:
        errors.append(f"{where}: release tag {url_tag!r} does not match version tag {tag!r}")
    if url_file != filename:
        errors.append(f"{where}: asset {url_file!r}, want {filename!r}")


def validate(doc):
    errors = []
    if not isinstance(doc, dict) or not isinstance(doc.get("plugins"), list) or not doc["plugins"]:
        return ["top level must be an object with a non-empty \"plugins\" array"]
    seen = set()
    for i, entry in enumerate(doc["plugins"]):
        manifest = entry.get("manifest") if isinstance(entry, dict) else None
        if not isinstance(manifest, dict):
            errors.append(f"plugins[{i}]: missing \"manifest\" object")
            continue
        pid = manifest.get("plugin_id")
        where = f"plugins[{i}] ({pid})"
        if not isinstance(pid, str) or not pid:
            errors.append(f"{where}: missing manifest.plugin_id")
        elif pid in seen:
            errors.append(f"{where}: duplicate plugin_id")
        seen.add(pid)
        version = manifest.get("version")
        if not isinstance(version, str) or not SEMVER.match(version):
            errors.append(f"{where}: manifest.version {version!r} is not semver")
            version = None
        tag = f"v{version}" if version else None

        repo = None
        parts = check_url(entry.get("repo_url"), f"{where}.repo_url", errors)
        if parts is not None:
            m = REPO_PATH.match(parts.path)
            if parts.netloc != "github.com" or not m:
                errors.append(f"{where}.repo_url: not a https://github.com/<owner>/<repo> URL")
            else:
                repo = (m.group(1).lower(), m.group(2).lower())

        check_asset(entry.get("checksums_url"), f"{where}.checksums_url", repo, tag, "checksums.txt", errors)

        binaries = entry.get("binaries")
        if not isinstance(binaries, dict) or not binaries:
            errors.append(f"{where}: missing \"binaries\" object")
            binaries = {}
        for platform, binary in binaries.items():
            bwhere = f"{where}.binaries[{platform!r}]"
            if not PLATFORM.match(platform):
                errors.append(f"{bwhere}: platform key must be os/arch")
                continue
            url = binary.get("url") if isinstance(binary, dict) else None
            check_asset(url, f"{bwhere}.url", repo, tag, "plugin-" + platform.replace("/", "-"), errors)

        platforms = manifest.get("supported_platforms") or []
        declared = {f"{p.get('os')}/{p.get('arch')}" for p in platforms if isinstance(p, dict)}
        if declared != set(binaries):
            errors.append(f"{where}: supported_platforms {sorted(declared)} != binaries {sorted(binaries)}")

        presentation = manifest.get("presentation") or {}
        for key, value in presentation.items():
            if key.endswith("_url") and value:
                check_url(value, f"{where}.manifest.presentation.{key}", errors)
    return errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "manifest.json"
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as err:
        print(f"{path}: does not parse: {err}", file=sys.stderr)
        return 1
    errors = validate(doc)
    for err in errors:
        print(f"{path}: {err}", file=sys.stderr)
    if errors:
        return 1
    print(f"{path}: {len(doc['plugins'])} plugin(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
