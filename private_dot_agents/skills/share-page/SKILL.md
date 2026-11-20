---
name: share-page
description: Share a static page, demo or built site on Cloudflare Pages, either public or behind Cloudflare Access for named emails. Use when the user asks to publish, host, deploy or share a page through Cloudflare, or to give or remove someone's access to a page shared this way.
---

# Share page

Every share is either **public** or **gated**. Gated means behind Cloudflare Access, with a one-time PIN sent by email, for a named list of addresses. If the user names people or says "behind auth", it is gated. If they say "public", it is public. If they say neither, ask which.

Cloudflare is reached through Executor's `cloudflare` integration. Read Executor's `skills({ name: "execute" })` first, then find each operation with `tools.search({ namespace: "cloudflare", query })` and `tools.describe.tool`. The operations below were verified; their shapes still come from `describe`.

- Results come back as JSON text in `data.content[0].text`.
- Zero Trust operations take `path: { account_or_zone: "accounts", account_or_zone_id }`.
- A delete pauses for approval. Resume it with `accept` only when the delete is one this workflow calls for.

## 1. Read the account

- **Account id:** `accounts_list`.
- **Who "me" is:** the email that the existing Access apps (`zerotrust_access_applications_list`) allow on every app. Confirm it with the account's name.
- **Sign-in method:** `zerotrust_identityproviders_list`. Use the `onetimepin` provider.
- **Name check:** reuse an app's settings when one already shares a page the same way.

Never write these values into a file. They differ per account and the dotfiles repo is public.

**Done when** you have the account id, the user's own email, the PIN provider id, and a project name that is free and says nothing confidential. The name becomes the public hostname `<name>.pages.dev`, so a client's name must not appear in it.

## 2. Get a deploy token

Wrangler on these hosts is usually not logged in (`bunx wrangler whoami`). If it isn't, mint a short-lived account token through `accounts_tokens_create`:
- It expires in 2 hours.
- It allows only `Pages Write` and `Account Settings Read`. Look up their ids with `accounts_tokens_permissiongroups_list`.

Pass the token to each command as `CLOUDFLARE_API_TOKEN` along with `CLOUDFLARE_ACCOUNT_ID`. Never write it to disk.

**Done when** `wrangler whoami` succeeds, or you hold a token id and value.

## 3. Create the project

```sh
bunx wrangler pages project create <name> --production-branch main --force
```

`--force` is needed only on this first command. Without it, wrangler hands off to Workers and fails with "Could not detect a directory containing static files". Commands after this don't need it.

## 4. Lock it (gated only)

The content must never be reachable without sign-in. Access needs about a minute after it is created before it starts enforcing. A real build deployed in that minute is public. So follow this order:

1. Create the Access app with `zerotrust_access_applications_create`:
   - `type: "self_hosted"`
   - `domain: "<name>.pages.dev"`
   - `self_hosted_domains: ["<name>.pages.dev", "*.<name>.pages.dev"]`. The wildcard covers the preview hostname of every deploy.
   - `session_duration: "730h"`, the maximum, unless the user asks for a shorter one.
   - `allowed_idps: [<PIN provider id>]`, `auto_redirect_to_identity: true`, `app_launcher_visible: false`
   - One `allow` policy with the same `session_duration`. It includes one `{ email: { email } }` per person, including the user's own email unless they say otherwise.
2. Deploy a blank placeholder (`<!doctype html><title>.</title>`) to `--branch main`.
3. Poll `curl -s -o /dev/null -w '%{http_code} %{redirect_url}' https://<name>.pages.dev/` until it returns `302` to `<team>.cloudflareaccess.com`. A `200` means Access is not enforcing yet.

**Done when** the production hostname returns that `302`.

## 5. Deploy

```sh
bunx wrangler pages deploy <dir> --project-name <name> --branch main [--commit-hash <sha> --commit-message "<subject>"]
```

Build the page first. A single-page app needs no redirects file, because Pages serves `index.html` for unknown paths when there is no `404.html`.

## 6. Verify and clean up

- **Gated:** check the production root, a deep asset path and the new preview hostname. Each must return `302` to Access.
  - A new project's preview hostnames fail TLS for a while (curl gives `000`). That is not exposure. Say that it is still pending.
  - Read the status code `curl` prints, never a body file. On a failed request `-o` leaves the previous file in place.
- **Public:** check that the root returns `200`.
- **Token:** delete the token from step 2 with `accounts_tokens_delete`.

**Done when** every hostname is verified or reported as pending, and no token you made still exists.

Report the URL, public or gated, who can sign in, the session length, and the redeploy command. If anything was briefly exposed, say so plainly.

## Changing access later

Find the app with `zerotrust_access_applications_list` and its policy with `zerotrust_access_applications_policies_list`. Update the policy's `include` list. Making a gated page public means deleting its Access app, so confirm that with the user first. Making a public page gated follows step 4 against the existing project.
