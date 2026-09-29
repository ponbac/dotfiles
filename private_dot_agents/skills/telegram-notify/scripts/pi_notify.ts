import { homedir } from "node:os"
import { join } from "node:path"
import { spawn } from "node:child_process"
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent"

const sender = join(
  homedir(),
  ".agents",
  "skills",
  "telegram-notify",
  "scripts",
  "telegram_notify.py",
)

function assistantText(messages: unknown[]): string {
  for (const candidate of [...messages].reverse()) {
    if (!candidate || typeof candidate !== "object") continue
    const message = candidate as {
      role?: string
      content?: string | Array<{ type?: string; text?: string }>
    }
    if (message.role !== "assistant") continue
    if (typeof message.content === "string") return message.content
    if (Array.isArray(message.content)) {
      return message.content
        .filter((part) => part?.type === "text" && typeof part.text === "string")
        .map((part) => part.text)
        .join("\n")
    }
  }
  return ""
}

function notify(message: string): Promise<void> {
  const body =
    message.length > 3900 ? `${message.slice(0, 3899).trimEnd()}…` : message
  return new Promise((resolve) => {
    const child = spawn(
      "python3",
      [sender, "--source", "Pi", "--stdin"],
      { stdio: ["pipe", "ignore", "pipe"] },
    )
    child.stderr.on("data", (chunk) => process.stderr.write(chunk))
    child.on("error", (error) => {
      console.error(`pi telegram notification failed: ${error.message}`)
      resolve()
    })
    child.on("close", () => resolve())
    child.stdin.end(body)
  })
}

export default function telegramNotify(pi: ExtensionAPI) {
  pi.on("agent_end", async (event, ctx) => {
    const summary = assistantText(event.messages as unknown[])
    const message = [
      "Task finished.",
      `Working directory: ${ctx.cwd}`,
      summary,
    ]
      .filter(Boolean)
      .join("\n\n")
    await notify(message)
  })
}
