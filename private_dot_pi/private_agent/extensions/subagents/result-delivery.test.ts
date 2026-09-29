import assert from "node:assert/strict";
import test from "node:test";
import {
  buildDeferredResultBatchContent,
  createDeferredResultDelivery,
} from "./result-delivery.ts";

test("a result consumed by a later wait is not delivered", () => {
  const delivery = createDeferredResultDelivery<{
    id: string;
    output: string;
  }>();

  delivery.defer({ id: "sa-1", output: "done" });
  delivery.consume(["sa-1"]);

  assert.deepEqual(delivery.drain(), []);
});

test("unconsumed results are drained once as one settlement-ordered batch", () => {
  const delivery = createDeferredResultDelivery<{ id: string }>();
  const first = { id: "sa-1" };
  const second = { id: "sa-2" };

  delivery.defer(first);
  delivery.defer(second);

  const batch = delivery.drain();
  assert.deepEqual(batch, [first, second]);
  assert.deepEqual(delivery.drain(), []);
});

test("a result batch requests one complete continuation instead of acknowledgements", () => {
  const content = buildDeferredResultBatchContent([
    'Subagent sa-1 "first" finished.\n\nFirst result',
    'Subagent sa-2 "second" finished.\n\nSecond result',
  ]);

  assert.match(content, /# 2 completed subagent results/);
  assert.ok(content.indexOf("First result") < content.indexOf("Second result"));
  assert.match(content, /Continue investigating, using tools, or spawning subagents as needed/);
  assert.match(content, /complete updated user-facing answer that supersedes earlier drafts/);
  assert.match(content, /do not merely acknowledge the results/);
});

test("an empty result batch does not request a continuation", () => {
  assert.equal(buildDeferredResultBatchContent([]), "");
});
