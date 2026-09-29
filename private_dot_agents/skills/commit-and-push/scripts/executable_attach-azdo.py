#!/usr/bin/env python3
"""Upload review media to an Azure DevOps PR and publish one comment thread."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen

AZDO_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"
IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png"}
VIDEO_EXTENSIONS = {".mov", ".mp4"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


class AttachError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Attach images/videos to an Azure DevOps PR and create one comment."
    )
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--organization", required=True, help="Organization name or URL")
    parser.add_argument("--project", required=True)
    parser.add_argument("--repository", required=True, help="Repository name or ID")
    parser.add_argument("--pr-id", required=True, type=int)
    body = parser.add_mutually_exclusive_group()
    body.add_argument("--body", help="Markdown placed before attachment references")
    body.add_argument("--body-file", type=Path, help="UTF-8 Markdown file")
    parser.add_argument(
        "--pat-env",
        default="AZURE_DEVOPS_EXT_PAT",
        help="Environment variable containing a PAT (default: AZURE_DEVOPS_EXT_PAT)",
    )
    parser.add_argument(
        "--max-size-mb",
        type=float,
        default=60.0,
        help="Defensive per-file limit; set to 0 to disable (default: 60)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and print planned comment")
    return parser.parse_args()


def organization_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if "://" not in value:
        return f"https://dev.azure.com/{quote(value, safe='')}"
    if not value.startswith("https://"):
        raise AttachError("--organization must be a name or an https:// URL")
    return value


def validate_files(paths: list[Path], max_size_mb: float) -> list[Path]:
    resolved: list[Path] = []
    names: set[str] = set()
    max_bytes = int(max_size_mb * 1024 * 1024)
    for path in paths:
        candidate = path.expanduser().resolve()
        if not candidate.is_file():
            raise AttachError(f"not a readable file: {path}")
        if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise AttachError(f"unsupported media type for {path}; expected one of: {allowed}")
        if candidate.name in names:
            raise AttachError(f"duplicate attachment filename: {candidate.name}")
        if max_bytes > 0 and candidate.stat().st_size > max_bytes:
            raise AttachError(f"{path} exceeds the configured {max_size_mb:g} MiB limit")
        names.add(candidate.name)
        resolved.append(candidate)
    return resolved


def authorization(pat_env: str) -> str:
    pat = os.environ.get(pat_env)
    if pat:
        token = base64.b64encode(f":{pat}".encode()).decode()
        return f"Basic {token}"
    try:
        result = subprocess.run(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                AZDO_RESOURCE,
                "--query",
                "accessToken",
                "--output",
                "tsv",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        raise AttachError(
            f"authentication failed: set {pat_env} or sign in with `az login` ({detail.strip()})"
        ) from error
    token = result.stdout.strip()
    if not token:
        raise AttachError(f"Azure CLI returned an empty access token; set {pat_env} instead")
    return f"Bearer {token}"


def request_json(
    method: str,
    url: str,
    auth: str,
    data: bytes | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    headers = {"Authorization": auth, "Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request) as response:
            payload = response.read()
    except HTTPError as error:
        payload = error.read().decode("utf-8", errors="replace")
        raise AttachError(f"{method} {url} failed with HTTP {error.code}: {payload}") from error
    except URLError as error:
        raise AttachError(f"{method} {url} failed: {error.reason}") from error
    if not payload:
        return {}
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise AttachError(f"{method} {url} returned invalid JSON") from error
    if not isinstance(value, dict):
        raise AttachError(f"{method} {url} returned an unexpected response")
    return value


def attachments_url(base: str, project: str, repository: str, pr_id: int) -> str:
    return (
        f"{base}/{quote(project, safe='')}/_apis/git/repositories/"
        f"{quote(repository, safe='')}/pullRequests/{pr_id}/attachments"
    )


def attachment_url(base: str, project: str, repository: str, pr_id: int, name: str) -> str:
    return f"{attachments_url(base, project, repository, pr_id)}/{quote(name, safe='')}?api-version=7.1"


def existing_attachment_names(response: dict[str, Any]) -> set[str]:
    values = response.get("value", [])
    if not isinstance(values, list):
        raise AttachError("attachment list returned an unexpected response")
    names: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        name = value.get("name") or value.get("fileName")
        if not isinstance(name, str):
            url = value.get("url")
            if isinstance(url, str):
                name = unquote(urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
        if isinstance(name, str) and name:
            names.add(name)
    return names


def threads_url(base: str, project: str, repository: str, pr_id: int) -> str:
    return (
        f"{base}/{quote(project, safe='')}/_apis/git/repositories/"
        f"{quote(repository, safe='')}/pullRequests/{pr_id}/threads?api-version=7.1"
    )


def media_markdown(path: Path, url: str) -> str:
    label = path.stem.replace("-", " ").replace("_", " ").strip() or path.name
    label = label.replace("[", "\\[").replace("]", "\\]")
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return f"![{label}]({url})"
    return f"[Download {label}]({url})"


def initial_body(args: argparse.Namespace) -> str:
    if args.body_file:
        try:
            return args.body_file.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise AttachError(f"cannot read body file {args.body_file}: {error}") from error
    return (args.body or "### Review evidence").strip()


def main() -> int:
    args = parse_args()
    try:
        files = validate_files(args.files, args.max_size_mb)
        body = initial_body(args)
        if args.dry_run:
            planned = body + "\n\n" + "\n\n".join(
                media_markdown(path, f"<uploaded-url-for-{path.name}>") for path in files
            )
            print(json.dumps({"dryRun": True, "files": [str(path) for path in files], "comment": planned}, indent=2))
            return 0

        base = organization_url(args.organization)
        auth = authorization(args.pat_env)
        existing = existing_attachment_names(
            request_json(
                "GET",
                attachments_url(base, args.project, args.repository, args.pr_id)
                + "?api-version=7.1",
                auth,
            )
        )
        collisions = sorted(path.name for path in files if path.name in existing)
        if collisions:
            raise AttachError(
                "the PR already has attachment(s) with these filenames: "
                + ", ".join(collisions)
            )

        uploaded: list[tuple[Path, str, str]] = []
        try:
            for path in files:
                endpoint = attachment_url(base, args.project, args.repository, args.pr_id, path.name)
                response = request_json(
                    "POST", endpoint, auth, path.read_bytes(), "application/octet-stream"
                )
                hosted_url = response.get("url")
                if not isinstance(hosted_url, str) or not hosted_url:
                    raise AttachError(f"upload response for {path.name} did not contain a URL")
                uploaded.append((path, hosted_url, endpoint))

            comment = body + "\n\n" + "\n\n".join(
                media_markdown(path, hosted_url) for path, hosted_url, _ in uploaded
            )
            payload = json.dumps(
                {
                    "comments": [
                        {"parentCommentId": 0, "content": comment, "commentType": 1}
                    ],
                    "status": 1,
                }
            ).encode()
            thread = request_json(
                "POST",
                threads_url(base, args.project, args.repository, args.pr_id),
                auth,
                payload,
                "application/json; charset=utf-8",
            )
        except Exception as publish_error:
            rollback_errors: list[str] = []
            for path, _, endpoint in reversed(uploaded):
                try:
                    request_json("DELETE", endpoint, auth)
                except Exception as rollback_error:
                    rollback_errors.append(f"{path.name}: {rollback_error}")
            if rollback_errors:
                cleanup = "rollback was incomplete: " + "; ".join(rollback_errors)
            else:
                cleanup = "all attachments uploaded by this invocation were rolled back"
            raise AttachError(f"publication failed; {cleanup}: {publish_error}") from publish_error

        print(
            json.dumps(
                {
                    "pullRequestId": args.pr_id,
                    "threadId": thread.get("id"),
                    "attachments": [
                        {"file": str(path), "url": hosted_url}
                        for path, hosted_url, _ in uploaded
                    ],
                },
                indent=2,
            )
        )
        return 0
    except AttachError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
