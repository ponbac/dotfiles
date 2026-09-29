const DEFERRED_RESULT_CONTINUATION_INSTRUCTION =
  "Incorporate these subagent results into the ongoing task. Continue investigating, using tools, or spawning subagents as needed. If the task is complete, respond with a complete updated user-facing answer that supersedes earlier drafts; do not merely acknowledge the results. Before finalizing, account for any still-running subagents whose results are needed.";

/**
 * Build one continuation message for every result available at a delivery
 * boundary. A single message produces a single parent continuation turn.
 */
export function buildDeferredResultBatchContent(
  resultSections: readonly string[],
): string {
  if (resultSections.length === 0) return "";

  const count = resultSections.length;
  return [
    DEFERRED_RESULT_CONTINUATION_INSTRUCTION,
    `# ${count} completed subagent ${count === 1 ? "result" : "results"}`,
    resultSections.join("\n\n---\n\n"),
  ].join("\n\n");
}

/**
 * Hold settled results until the parent reaches a safe delivery boundary.
 * Draining atomically transfers all currently pending results to one batch.
 */
export function createDeferredResultDelivery<T extends { id: string }>() {
  const pending = new Map<string, T>();

  return {
    defer(result: T) {
      pending.set(result.id, result);
    },
    consume(ids: Iterable<string>) {
      for (const id of ids) pending.delete(id);
    },
    drain() {
      const results = [...pending.values()];
      pending.clear();
      return results;
    },
    clear() {
      pending.clear();
    },
  };
}
