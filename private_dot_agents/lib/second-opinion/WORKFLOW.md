# Second opinion

Give the other harness the user's requirements, the changes to review, relevant constraints, and verification already performed. Make the scope clear enough to distinguish your work from unrelated changes, including untracked files where relevant. Supply context rather than an argument that your implementation is correct.

Read `~/.agents/lib/second-opinion/review-contract.md` and include its guidance in the reviewer prompt. Encourage native sub-agents to shard the review as they see fit; ask the lead reviewer to return consolidated, evidence-bearing findings.

Invoke the CLI directly using the invoking skill's model, reasoning, and YOLO settings. Let the reviewer inspect the repository and run checks freely. Pause your own edits while it reviews the same checkout. Use your harness's normal long-running or background execution facilities and allow enough time for a substantive review. Keep the response and useful diagnostics somewhere you can inspect afterward; there is no required file layout or wrapper.

Keep cross-harness review to one hop. A reviewer and its native sub-agents return findings rather than launching another cross-harness review.

Wait for a completed response. A startup failure, timeout, or incomplete review is not a clean verdict. If execution fails, inspect the diagnostics and adjust the launch as needed without silently changing the requested model.

Assess each finding against the requirements and code: accept it, reject it with evidence, or identify it as unresolved. Account for any modifications the reviewer made. Summarize the useful findings and coverage limitations to the user, then apply accepted fixes and re-run verification when the original task authorizes implementation.
