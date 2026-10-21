# Serving a walkthrough on the tailnet

Serve the page to the user's tailnet only. `tailscale funnel` would publish it to the internet, so use it only when the user asks for public access by name.

A non-root user can't serve a file or directory with `tailscale serve`; it returns `401 ... must be root`. Instead, proxy a local HTTP server that holds only this page.

1. **Check Tailscale.** Run `tailscale status` to confirm it's up. Get the host from `tailscale status --json` as `Self.DNSName`, minus the trailing dot.
2. **Pick ports.** Run `tailscale serve status` and note which HTTPS ports are taken, since other services may already own `/` on 443. Choose a free HTTPS port (for example 8460–8499) and a free local port.
3. **Serve a directory holding only this page,** so no other page in `~/.agent/diagrams` is exposed:

   ```sh
   dir=~/.agent/diagrams/serve/pr-<n>
   mkdir -p "$dir" && ln -sf ~/.agent/diagrams/pr-<n>-<slug>.html "$dir/index.html"
   setsid nohup python3 -m http.server <local-port> --bind 127.0.0.1 --directory "$dir" >/dev/null 2>&1 &
   tailscale serve --bg --yes --https=<https-port> http://127.0.0.1:<local-port>
   ```

   The symlink means later edits to the page show up without serving again. Symlink any video saved next to the page into the same directory.
4. **Verify.** `curl -s -o /dev/null -w "%{http_code} %{content_type}\n" https://<host>:<https-port>/` returns `200 text/html`.
5. **Hand over.**
   - Give the user `https://<host>:<https-port>/`.
   - Say that it stays up until removed, and that the page's web fonts, Mermaid and Shiki load from the viewer's own connection.
   - Give the teardown, which removes only this page's serve:

   ```sh
   tailscale serve --https=<https-port> off
   pkill -f "http.server <local-port>"
   ```

   Any other serve configuration stays as it is. `tailscale serve reset` would wipe all of it, so leave that out of the teardown.
