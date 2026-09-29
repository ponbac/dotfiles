---
name: web-design-guidelines
description: Review UI code against the Web Interface Guidelines (accessibility, focus, forms, motion, typography, dark mode, i18n, touch) and report findings as file:line. Use only when the user explicitly invokes web-design-guidelines by name.
disable-model-invocation: true
license: MIT
metadata:
  author: vercel
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review UI files for compliance with the Web Interface Guidelines.

1. Read the rules and output format in [GUIDELINES.md](GUIDELINES.md). They are a pinned local copy; do not fetch them from the web.
2. Review the files or pattern the user passed. If none were given, ask which files to review.
3. Check every file against all rules and report findings in the format GUIDELINES.md specifies.
