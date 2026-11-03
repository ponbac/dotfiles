- Executor (`execute` tool) is the route to Slack, Gon, mail, calendar and other connected services. Try it before saying you can't reach someone.
- If you're stuck on auth and can't get past it without the user doing something by hand, message Gon through Executor. Gon can reach the user. Say exactly what you need from them.
- Gon's box (`grokbot-box`) sleeps when idle and shows as offline in Tailscale. A message through Executor wakes it, so never skip or delay a Gon message because the box looks offline. If Taildrop fails because the box is asleep, send the message anyway, then send the files in a follow-up once the box is online.
- Open every PR with the `commit-and-push` skill. A repository's own PR rules or template take precedence.
- Start every comment posted under the user's account with this note, then a blank line:

  ```
  > [!NOTE]
  > 🤖 **<model> responding on behalf of <user>**
  ```

  On Azure DevOps, use only the `> 🤖 …` line. Skip the note for `@codex review` and text the user wants posted verbatim.
