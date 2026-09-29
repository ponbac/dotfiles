import { homedir } from "node:os"
import { join } from "node:path"
import { spawn } from "node:child_process"

const sender = join(
  homedir(),
  ".agents",
  "skills",
  "telegram-notify",
  "scripts",
  "telegram_notify.py",
)

function notify(message) {
  return new Promise((resolve) => {
    const child = spawn(
      "python3",
      [sender, "--source", "OpenCode", "--stdin"],
      { stdio: ["pipe", "ignore", "pipe"] },
    )
    child.stderr.on("data", (chunk) => process.stderr.write(chunk))
    child.on("error", (error) => {
      console.error(`opencode telegram notification failed: ${error.message}`)
      resolve()
    })
    child.on("close", () => resolve())
    child.stdin.end(message)
  })
}

export const TelegramNotifyPlugin = async ({ directory }) => ({
  event: async ({ event }) => {
    if (event.type === "session.idle") {
      await notify(`Task finished.\n\nWorking directory: ${directory}`)
    }
    if (event.type === "session.error") {
      await notify(`Session error.\n\nWorking directory: ${directory}`)
    }
  },
})
