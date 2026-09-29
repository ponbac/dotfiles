import {
	AgentSession,
	type ExtensionAPI,
	type ExtensionContext,
	type PromptOptions,
} from "@earendil-works/pi-coding-agent";

const SELF_COMPACT_COMMAND = "self-compact";
const CONTROL_CUSTOM_TYPE = "ponbac:self-compact-control:v1";
const PATCHED = Symbol.for("ponbac.self-compact.patch.v2");
const QUEUE_PATCHED = Symbol.for("ponbac.self-compact.queue-patch.v1");

type QueueMode = "steer" | "followUp";

type SelfCompactControlDetails = {
	text: string;
	mode: QueueMode;
	customInstructions?: string;
};

type QueueLike = {
	messages: unknown[];
	mode: "all" | "one-at-a-time";
	drain: () => unknown[];
};

type AgentSessionInternals = {
	agent: {
		state: AgentSession["agent"]["state"];
		steeringQueue: QueueLike;
		followUpQueue: QueueLike;
		steer: AgentSession["agent"]["steer"];
		followUp: AgentSession["agent"]["followUp"];
		hasQueuedMessages: AgentSession["agent"]["hasQueuedMessages"];
	};
	isStreaming: boolean;
	prompt: AgentSession["prompt"];
	compact: AgentSession["compact"];
	_steeringMessages: string[];
	_followUpMessages: string[];
	_lastAssistantMessage?: AgentSession["agent"]["state"]["messages"][number];
	_retryAttempt: number;
	_emit: (event: unknown) => void;
	_emitQueueUpdate: () => void;
	_isRetryableError: (message: unknown) => boolean;
	_prepareRetry: (message: unknown) => Promise<boolean>;
	_checkCompaction: (message: unknown) => Promise<boolean>;
	_handlePostAgentRun: () => Promise<boolean>;
};

let compactionRunning = false;

function normalizeInstructions(value: string | undefined): string | undefined {
	const trimmed = value?.trim();
	return trimmed ? trimmed : undefined;
}

function notify(ctx: ExtensionContext, message: string, level: "info" | "warning" | "error"): void {
	if (ctx.hasUI) {
		ctx.ui.notify(message, level);
	}
}

function triggerCompaction(ctx: ExtensionContext, customInstructions?: string): "started" | "already-running" {
	if (compactionRunning) {
		notify(ctx, "Compaction is already running.", "warning");
		return "already-running";
	}

	compactionRunning = true;
	notify(ctx, customInstructions ? `Compaction started: ${customInstructions}` : "Compaction started.", "info");

	ctx.compact({
		customInstructions,
		onComplete: (result) => {
			compactionRunning = false;
			notify(ctx, `Compaction completed. Replaced ~${result.tokensBefore.toLocaleString()} tokens.`, "info");
		},
		onError: (error) => {
			compactionRunning = false;
			notify(ctx, `Compaction failed: ${error.message}`, "error");
		},
	});

	return "started";
}

function parseSelfCompactRequest(text: string): string | undefined | null {
	const trimmed = text.trim();
	if (!trimmed) {
		return null;
	}

	if (trimmed === `/${SELF_COMPACT_COMMAND}`) {
		return undefined;
	}

	if (trimmed.startsWith(`/${SELF_COMPACT_COMMAND} `)) {
		return normalizeInstructions(trimmed.slice(SELF_COMPACT_COMMAND.length + 2));
	}

	if (trimmed.startsWith("/")) {
		return null;
	}

	const match = trimmed.match(
		/^(?:please\s+)?(?:(?:self[-\s]?compact)|(?:compact(?:\s+(?:yourself|now|context|conversation|session))?))(?:\s*(?::|—|-)\s*|\s+with\s+)?([\s\S]*)$/i,
	);

	if (!match) {
		return null;
	}

	return normalizeInstructions(match[1]);
}

function isSelfCompactControlMessage(message: unknown): message is { details: SelfCompactControlDetails } {
	if (!message || typeof message !== "object") {
		return false;
	}
	const candidate = message as { role?: unknown; customType?: unknown; details?: unknown };
	return candidate.role === "custom" && candidate.customType === CONTROL_CUSTOM_TYPE;
}

function patchQueue(queue: QueueLike): void {
	const queueRecord = queue as QueueLike & { [QUEUE_PATCHED]?: true };
	if (queueRecord[QUEUE_PATCHED]) {
		return;
	}

	const originalDrain = queue.drain.bind(queue);
	Object.defineProperty(queueRecord, QUEUE_PATCHED, { value: true });

	queue.drain = function patchedDrain(this: QueueLike): unknown[] {
		const controlIndex = this.messages.findIndex(isSelfCompactControlMessage);
		if (controlIndex === -1) {
			return originalDrain();
		}

		// Stop the running agent exactly when the self-compact marker reaches the
		// front of the queue. AgentSession._handlePostAgentRun then performs the
		// compaction before continuing with messages behind the marker.
		if (controlIndex === 0) {
			return [];
		}

		// In "all" mode, drain only messages before the marker so compaction still
		// happens at the marker's queue position.
		if (this.mode === "all") {
			const drained = this.messages.slice(0, controlIndex);
			this.messages = this.messages.slice(controlIndex);
			return drained;
		}

		return originalDrain();
	};
}

function queueForMode(session: AgentSessionInternals, mode: QueueMode): QueueLike {
	return mode === "steer" ? session.agent.steeringQueue : session.agent.followUpQueue;
}

function displayQueueForMode(session: AgentSessionInternals, mode: QueueMode): string[] {
	return mode === "steer" ? session._steeringMessages : session._followUpMessages;
}

function enqueueSelfCompactControl(
	session: AgentSessionInternals,
	mode: QueueMode,
	text: string,
	customInstructions?: string,
): void {
	const queue = queueForMode(session, mode);
	patchQueue(queue);

	const message = {
		role: "custom" as const,
		customType: CONTROL_CUSTOM_TYPE,
		content: "",
		display: false,
		details: { text, mode, customInstructions } satisfies SelfCompactControlDetails,
		timestamp: Date.now(),
	};

	displayQueueForMode(session, mode).push(text);
	if (mode === "steer") {
		session.agent.steer(message);
	} else {
		session.agent.followUp(message);
	}
	session._emitQueueUpdate?.();
}

function takeFrontSelfCompactControl(session: AgentSessionInternals): SelfCompactControlDetails | undefined {
	for (const mode of ["steer", "followUp"] as const) {
		const queue = queueForMode(session, mode);
		patchQueue(queue);

		const first = queue.messages[0];
		if (!isSelfCompactControlMessage(first)) {
			continue;
		}

		queue.messages.splice(0, 1);

		const details = first.details;
		const displayQueue = displayQueueForMode(session, mode);
		const displayIndex = displayQueue.indexOf(details.text);
		if (displayIndex !== -1) {
			displayQueue.splice(displayIndex, 1);
		}
		session._emitQueueUpdate?.();

		return details;
	}

	return undefined;
}

async function compactAtQueuePosition(
	session: AgentSessionInternals,
	customInstructions?: string,
): Promise<void> {
	// AgentSession.compact() begins by calling abort(), which waits for the
	// session-level run to become idle. This hook runs after the Agent itself is
	// idle but before AgentSession clears _isAgentRunActive. Calling compact()
	// directly here therefore waits for _handlePostAgentRun() to return while
	// _handlePostAgentRun() waits for compact(): a deadlock.
	//
	// SAFETY: No asynchronous work can observe the temporary state change. An
	// async function executes synchronously until its first await, so compact()
	// reaches abort().waitForIdle() and observes the already-idle Agent before we
	// restore the session-level flag. The flag remains true for the actual
	// compaction and any subsequent queued continuation.
	const runState = session as unknown as { _isAgentRunActive: boolean };
	const wasAgentRunActive = runState._isAgentRunActive;
	runState._isAgentRunActive = false;
	let compaction: Promise<unknown>;
	try {
		compaction = session.compact(customInstructions);
	} finally {
		runState._isAgentRunActive = wasAgentRunActive;
	}
	await compaction;
}

async function compactQueuedControl(
	session: AgentSessionInternals,
	control: SelfCompactControlDetails,
): Promise<void> {
	if (session.agent.state.isStreaming) {
		throw new Error("Cannot compact before the active Agent run has finished.");
	}

	try {
		await compactAtQueuePosition(session, control.customInstructions);
	} catch {
		// session.compact() emits compaction_end with the failure. A failed manual
		// compaction must not prevent messages behind the marker from continuing.
	}
}

function patchAgentSessionForQueuedSelfCompact(): void {
	const prototype = AgentSession.prototype as unknown as AgentSessionInternals & { [PATCHED]?: true };
	if (prototype[PATCHED]) {
		return;
	}
	Object.defineProperty(prototype, PATCHED, { value: true });

	const originalPrompt = prototype.prompt;
	prototype.prompt = async function patchedPrompt(
		this: AgentSessionInternals,
		text: string,
		options?: PromptOptions,
	) {
		const customInstructions = parseSelfCompactRequest(text);
		const canInterceptQueuedInput =
			this.isStreaming &&
			options?.streamingBehavior !== undefined &&
			options.source !== "extension" &&
			!options.images?.length;
		if (customInstructions !== null && canInterceptQueuedInput) {
			const streamingBehavior = options?.streamingBehavior;
			if (streamingBehavior === undefined) {
				throw new Error("Queued self-compaction requires a streaming behavior.");
			}
			enqueueSelfCompactControl(this, streamingBehavior, text.trim(), customInstructions);
			options.preflightResult?.(true);
			return;
		}

		return originalPrompt.call(this, text, options);
	};

	prototype._handlePostAgentRun = async function patchedHandlePostAgentRun(
		this: AgentSessionInternals,
	): Promise<boolean> {
		const msg = this._lastAssistantMessage;
		this._lastAssistantMessage = undefined;

		if (!msg) {
			const control = takeFrontSelfCompactControl(this);
			if (!control) {
				return false;
			}

			await compactQueuedControl(this, control);
			return this.agent.hasQueuedMessages();
		}

		if (this._isRetryableError(msg) && (await this._prepareRetry(msg))) {
			return true;
		}

		if (msg.role === "assistant" && msg.stopReason === "error" && this._retryAttempt > 0) {
			this._emit({
				type: "auto_retry_end",
				success: false,
				attempt: this._retryAttempt,
				finalError: msg.errorMessage,
			});
			this._retryAttempt = 0;
		}

		// A queued manual compaction takes precedence over threshold compaction at
		// the same boundary. Otherwise auto-compaction can report a pending queue,
		// AgentSession calls agent.continue(), and the control marker's patched
		// drain intentionally returns no message from an assistant-ended run.
		const control = takeFrontSelfCompactControl(this);
		if (control) {
			await compactQueuedControl(this, control);
			return this.agent.hasQueuedMessages();
		}

		if (await this._checkCompaction(msg)) {
			return true;
		}

		return this.agent.hasQueuedMessages();
	};
}

export default function (pi: ExtensionAPI) {
	patchAgentSessionForQueuedSelfCompact();

	pi.registerCommand(SELF_COMPACT_COMMAND, {
		description: "Trigger Pi context compaction; when queued, runs at its queue position",
		handler: async (args, ctx) => {
			triggerCompaction(ctx, normalizeInstructions(args));
		},
	});

	pi.on("input", (event, ctx) => {
		if (event.source === "extension" || event.images?.length) {
			return { action: "continue" as const };
		}

		const customInstructions = parseSelfCompactRequest(event.text);
		if (customInstructions === null || event.text.trim().startsWith("/")) {
			return { action: "continue" as const };
		}

		triggerCompaction(ctx, customInstructions);
		return { action: "handled" as const };
	});
}
