import { execFile } from "node:child_process";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const STATUS_KEY = "jj-status";
const REFRESH_MS = 5_000;
const COMMAND_TIMEOUT_MS = 1_500;

type JjSummary = {
	changeId: string;
	commitId: string;
	description: string;
	bookmarks: string;
	empty: boolean;
	conflict: boolean;
	changes: {
		modified: number;
		added: number;
		deleted: number;
		renamed: number;
		copied: number;
		unknown: number;
	};
};

export default function (pi: ExtensionAPI) {
	let interval: ReturnType<typeof setInterval> | undefined;
	let refreshing = false;
	let lastText: string | undefined;

	async function refresh(ctx: ExtensionContext) {
		if (refreshing) return;
		refreshing = true;
		try {
			const text = await getStatusText(process.cwd(), ctx);
			if (text !== lastText) {
				ctx.ui.setStatus(STATUS_KEY, text);
				lastText = text;
			}
		} catch {
			if (lastText !== undefined) {
				ctx.ui.setStatus(STATUS_KEY, undefined);
				lastText = undefined;
			}
		} finally {
			refreshing = false;
		}
	}

	pi.on("session_start", async (_event, ctx) => {
		if (interval) clearInterval(interval);
		await refresh(ctx);
		interval = setInterval(() => void refresh(ctx), REFRESH_MS);
	});

	pi.on("input", async (_event, ctx) => {
		await refresh(ctx);
	});

	pi.on("tool_execution_end", async (_event, ctx) => {
		await refresh(ctx);
	});

	pi.on("turn_end", async (_event, ctx) => {
		await refresh(ctx);
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		if (interval) clearInterval(interval);
		interval = undefined;
		ctx.ui.setStatus(STATUS_KEY, undefined);
		lastText = undefined;
	});
}

async function getStatusText(cwd: string, ctx: ExtensionContext): Promise<string | undefined> {
	const root = await runJj(["root"], cwd).catch(() => undefined);
	if (!root?.trim()) return undefined;

	const repoCwd = root.trim();
	const starshipStatus = await getStarshipJjStatus(repoCwd).catch(() => undefined);
	if (starshipStatus) return formatStarshipStatus(starshipStatus, ctx);

	const summary = await getJjSummary(repoCwd);
	return summary ? formatStatus(summary, ctx) : undefined;
}

async function getStarshipJjStatus(cwd: string): Promise<string | undefined> {
	const output = await runCommand("starship-jj", ["--color", "never", "--ignore-working-copy", "starship", "prompt"], cwd);
	const text = output
		.replace(/\x1b\[[0-9;]*m/g, "")
		.replace(/\r?\n/g, " ")
		.replace(/^󱗆\s*/, "")
		.trim();
	return text || undefined;
}

function formatStarshipStatus(text: string, ctx: ExtensionContext): string {
	const theme = ctx.ui.theme;
	return `${theme.fg("accent", "jj")} ${theme.fg("dim", text)}`;
}

async function getJjSummary(repoCwd: string): Promise<JjSummary | undefined> {
	const [log, status] = await Promise.all([
		runJj(
			[
				"--no-pager",
				"log",
				"--no-graph",
				"-r",
				"@",
				"-T",
				'change_id.shortest(8) ++ "\t" ++ commit_id.shortest(8) ++ "\t" ++ if(empty, "1", "0") ++ "\t" ++ if(conflict, "1", "0") ++ "\t" ++ bookmarks.join(" ") ++ "\t" ++ if(description, description.first_line(), "")',
			],
			repoCwd,
		),
		runJj(["--no-pager", "status", "--color", "never"], repoCwd),
	]);

	const [changeId = "?", commitId = "?", empty = "0", conflict = "0", bookmarks = "", description = ""] = log.trim().split("\t");

	return {
		changeId,
		commitId,
		empty: empty === "1",
		conflict: conflict === "1",
		bookmarks,
		description,
		changes: parseStatus(status),
	};
}

function runJj(args: string[], cwd: string): Promise<string> {
	return runCommand("jj", args, cwd, { ...process.env, NO_COLOR: "1" });
}

function runCommand(command: string, args: string[], cwd: string, env = process.env): Promise<string> {
	return new Promise((resolve, reject) => {
		execFile(command, args, { cwd, timeout: COMMAND_TIMEOUT_MS, env }, (error, stdout) => {
			if (error) reject(error);
			else resolve(stdout);
		});
	});
}

function parseStatus(status: string): JjSummary["changes"] {
	const changes = { modified: 0, added: 0, deleted: 0, renamed: 0, copied: 0, unknown: 0 };
	for (const line of status.split("\n")) {
		if (/^M\s/.test(line) || /^Modified\b/.test(line)) changes.modified++;
		else if (/^A\s/.test(line) || /^Added\b/.test(line)) changes.added++;
		else if (/^D\s/.test(line) || /^Deleted\b/.test(line)) changes.deleted++;
		else if (/^R\s/.test(line) || /^Renamed\b/.test(line)) changes.renamed++;
		else if (/^C\s/.test(line) || /^Copied\b/.test(line)) changes.copied++;
		else if (/^\?\s/.test(line) || /^\?\?\s/.test(line)) changes.unknown++;
	}
	return changes;
}

function formatStatus(summary: JjSummary, ctx: ExtensionContext): string {
	const theme = ctx.ui.theme;
	const parts = [theme.fg("accent", "jj"), theme.fg(summary.conflict ? "error" : "dim", summary.changeId)];

	if (summary.bookmarks) parts.push(theme.fg("success", summary.bookmarks));
	else if (summary.description) parts.push(theme.fg("dim", truncate(summary.description, 24)));
	else if (summary.empty) parts.push(theme.fg("dim", "empty"));

	const counts = formatChangeCounts(summary.changes);
	if (counts) parts.push(theme.fg("warning", counts));
	if (summary.conflict) parts.push(theme.fg("error", "conflict"));

	return parts.join(" ");
}

function formatChangeCounts(changes: JjSummary["changes"]): string {
	const parts: string[] = [];
	if (changes.modified) parts.push(`~${changes.modified}`);
	if (changes.added) parts.push(`+${changes.added}`);
	if (changes.deleted) parts.push(`-${changes.deleted}`);
	if (changes.renamed) parts.push(`→${changes.renamed}`);
	if (changes.copied) parts.push(`⧉${changes.copied}`);
	if (changes.unknown) parts.push(`?${changes.unknown}`);
	return parts.join(" ");
}

function truncate(value: string, max: number): string {
	return value.length <= max ? value : `${value.slice(0, Math.max(0, max - 1))}…`;
}
