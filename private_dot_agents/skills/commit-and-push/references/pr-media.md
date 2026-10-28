# PR review media

Use PR-hosted attachments for review evidence that should not be committed to the repository.

## Selection and safety

- Attach media only when it materially helps a reviewer understand or verify the change: UI before/after states, a hard-to-describe interaction, animation, rendering, or a visual regression.
- Consider only files explicitly produced or identified as review evidence for the current task. Do not search the checkout or home directory for arbitrary media.
- A request to run this skill authorizes publishing relevant review-evidence files already identified in the task. It does not authorize uploading unrelated generated files.
- Before upload, inspect every file for secrets, tokens, customer/personal data, private URLs, notifications, browser chrome, unrelated applications, and misleading or stale state. Ask before publishing when sensitivity or relevance is uncertain.
- Treat attachment URLs as shareable. For a public GitHub repository, mention that the media will be public and ask before upload unless the user explicitly requested that those files be attached or published.
- Prefer one concise comment. Use images for static states and video only when motion or sequencing adds information. Do not attach redundant media.
- Keep evidence outside tracked source paths when practical. Never add media to Git solely to make it available to a PR.

## GitHub

Requires GitHub CLI v2.99.0 or newer and write access.

```bash
gh pr comment <number> --repo <owner/repo> \
  --body-file ./artifacts/pr-evidence.md \
  --attach ./artifacts/result.png \
  --attach ./artifacts/demo.mp4
```

`./artifacts/pr-evidence.md`:

```markdown
### Review evidence

**Result after the change:**

![Result after the change](./result.png)
```

`--attach` supports PNG, GIF, JPEG, SVG, MP4, MOV, and WebM. Validate current provider limits before upload; as a conservative baseline, keep images at or below 10 MiB. Video limits vary by GitHub plan.

`gh` rewrites only Markdown references to an attached file, `![alt](path)`, and resolves their paths relative to the body file's directory, then the working directory. A bare path or a plain-text filename is not a reference: it stays in the comment as literal text, and `gh` appends the upload at the end of the comment instead. To place media inline:

- Reference every attached image with `![alt](path)`, using exactly the path passed to `--attach` or one relative to the body file. Keep the body file next to the media so the references can be `./name.png`.
- Put each reference in its own paragraph. The inline reference form for video is unverified, so leave videos unreferenced and let `gh` append them, in their own paragraph at the end, where GitHub renders a player.
- After posting, read the comment back (`gh api repos/<owner>/<repo>/issues/comments/<id> --jq .body`). It must contain no local paths, and no image may be appended after the final section. If it does, edit the comment so each uploaded URL replaces its path; do not post a second comment.

Do not call GitHub's undocumented internal upload endpoints. If `gh` is older than v2.99.0, stop and report the required upgrade rather than falling back to browser automation.

## Azure DevOps

Use `../scripts/attach-azdo.py`. It uploads raw bytes through the official PR Attachments REST API, creates one general PR thread, and attempts to delete every attachment uploaded by that invocation if thread creation fails.

```bash
python3 ~/.agents/skills/commit-and-push/scripts/attach-azdo.py \
  --organization https://dev.azure.com/<org> \
  --project '<project>' \
  --repository '<repo-name-or-id>' \
  --pr-id <id> \
  --body '### Review evidence' \
  ./artifacts/result.png ./artifacts/demo.mp4
```

Authentication uses `AZURE_DEVOPS_EXT_PAT` as a PAT when set. Otherwise it requests an Azure DevOps bearer token from the current `az login` session. Never pass a token on the command line.

The helper accepts PNG, GIF, JPEG, MP4, and MOV. It uses a conservative 60 MiB per-file safety limit, configurable with `--max-size-mb`. Images are embedded; videos are linked because Azure DevOps does not guarantee inline playback in PR comments. Use `--dry-run` to validate files and preview Markdown without authentication or network access.

The attachment and thread operations require code write permission. The rollback is best-effort: if deletion fails, report the orphaned attachment filenames and do not claim complete cleanup.

## Repository-state check

Capture repository state immediately before publication and compare it afterward:

- Git worktree mode: `git status --porcelain=v1 --untracked-files=all`
- JJ mode: `jj status`

Attachment publication should not modify repository state. If it changed, report the difference and do not silently clean or commit it.

## Primary documentation

- GitHub CLI attachments: <https://docs.github.com/en/github-cli/github-cli/attaching-files-with-github-cli>
- GitHub attachment formats and limits: <https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files>
- Azure PR attachment create/delete: <https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-attachments/create?view=azure-devops-rest-7.1>
- Azure PR thread creation: <https://learn.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-threads/create?view=azure-devops-rest-7.1>
