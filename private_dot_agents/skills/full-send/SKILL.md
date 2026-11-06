---
name: full-send
description: 'Take a change all the way to merged with nobody watching. Use when the user says "full send", or "crossbuild" with `finish: merge`.'
---

# Full send

The user said this because they aren't watching. Treat them as away. It's permission to merge this PR, in any repository, once the merge gate passes.

1. **Run `full-stop`.** Follow it through its babysit step. Its merge ban doesn't apply here.
2. **Prove the final diff.** Your proof must cover every change on the latest commit. Prove anything added since the last proof.
3. **Merge.** Continue `babysit` through to the merge. Its step 5 is the merge gate. If the gate can't pass, leave the PR open and ask, following `full-stop`'s rules for asking.
4. **Report.** Give the PR link, the merge result, your proof, the review verdict, and each decision you made for the user.
