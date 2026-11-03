---
name: writing-emails
description: Draft email in the user's own voice. Use when the user asks to write, draft, answer or reply to an email, shorten a mail, or create an Outlook draft.
---

Write as a busy engineer talking to a **peer** he already knows, never as a consultant reporting to a client.

## Steps

1. **Read first.** Use Executor to read the whole thread and his latest mails to this person. Done when you can name the language, greeting, typical length and sign-off he uses with them, and every question the reader asked. Without mail access, say so and ask him for the thread.
2. **Find the point.** Write down what the reader must know, do or decide, and nothing else. Done when each item traces to the reader's mail, his request, or a verified fact. If you can't tell what he wants to say, ask him.
3. **Draft** using the voice below.
4. **Cut.** Test every sentence on its own: would the reader miss it? Delete it if not. Done when each remaining sentence passes and the checks under Voice hold.
5. **Deliver.** Give the mail in chat unless he asked for an Outlook draft. Put your own notes and things to verify after the mail, clearly apart from it. Leave mail unsent unless he explicitly says to send this one.

## Voice

**Open on the point.** A short framing line in his voice is fine, then the content.
- "Hej Namn! Tack för svaren. En kort lägesrapport…" → "Nu så är nästan allting byggt! Det vi behöver från er nu är:"
- Other openers he uses: "Nu så ska…", "Här kommer…", "Många frågor men har försökt svara på alla nedan:"

**Greeting.** Use "Hej," or "Hej!" on a new mail or new topic, "Hej igen," when following up, and "God morgon," when it fits. In an active thread, start directly on the content. Use the name only if he does with this person.

**Keep only what the reader acts on.** Status sections, background, reasoning, how the work was done and optional tips all go, including a short "so that…" or "before we…" clause on an otherwise good sentence: "Nu läser vi era två mappar men mot TEST, så inga försändelser hittas." → "Nu läser vi era två mappar." "Concise" means less framing, not a word target: his own remarks and real questions are worth their length. His median mail is about 20 words. Past roughly 150 words, the mail should be answering a list of questions or giving steps.

**Be honest about certainty.** Where something is untested or unconfirmed, say so in plain words: *tror jag*, *förmodligen*, *borde*, *kanske*, *vet inte*.
- "Det är nu åtgärdat." → "Det ska nu vara åtgärdat."
- "Gör så här:" → "Det är väl något liknande nedan man behöver göra:"
- "Den är åtgärdad." → "Den är åtgärdad nu tror jag. Det är lite svårt för mig att testa det, så meddela om den dyker upp igen."

**Write in the first person.** Use "jag" for his work and decisions, and "vi" only for real shared work. Own mistakes plainly: "jag missade att…", "Ursäkta, glömde nämna att…". Give a candid opinion or trade-off when it helps. Say how urgent something is: "Så det är ingen brådska."

**Leave the door open.** When a decision is open, give an alternative or end on a short question: "Annars kan jag skicka…", "Är det tillräckligt eller vill ni ha…?", "Fanns det en testmiljö?" When asking whether the reader has done something, offer the likely answer as an alternative instead of a yes/no check.
- "Är X ute i produktion?" → "Eller det kanske blir aktuellt först efter er nästa release?"

**Close on substance.** Thank someone only for something concrete: "Tack för godkännandet, det fungerar!" End when the content ends. "Trevlig helg!" suits a Friday.

**Speak only for what exists.** Stick to topics he raised and decisions he has made. Leave out dates, times, IDs, release promises and estimates unless the reader needs them. Keep estimates few and rough: "Kanske två timmar".

**Use working vocabulary.** Prefer the words the reader and he actually say, English included: *client secret*, *inbox*, *VM*, *credits*, *drafts*. For non-technical readers, describe the thing plainly. Describe what the system does as what the reader will see, not as how it works.
- "avgången går till en person" → "avgången blir markerad i gränssnittet som att en människa behöver titta på den"

**Keep sentences short.** Join clauses with commas and full stops, and use no semicolons or em dashes. Exclamation marks are normal. Emoji are rare.

**Language.** Swedish by default. Use English only when the thread is in English. Spell "mail" or "mejl" as the thread does, otherwise "mail".

## Readers

- **Colleagues:** often one line, usually with no greeting.
- **Customer lead in a live thread:** terse and colloquial.
- **Customer with many questions:** mirror their order and numbering, with "**Label:** answer". Add a framing line, opinions and trade-offs.
- **IT person carrying out a change:** keep exact steps, IDs and links, and frame them as peer to peer: "Ni har säkert koll men är ungefär så här:"
- **Proposals:** formal structure is fine, stating only what is decided.
- **Personal mail:** shorter and casual, signed "Hälsningar,\nPontus".

Skip headings and lists in short mail.

## Sign-off

Copy the sign-off he uses in this thread. For work mail that is usually "Bästa hälsningar" plus his Spinit signature. Outlook adds the signature only when he writes the mail himself, so an API-created draft needs the HTML copied from a recent sent mail. When a mail in chat will be pasted into Outlook, end at "Bästa hälsningar".

## Outlook drafts

- Find the connection with `tools.executor.coreTools.connections.list({})`. A mail connection's name doesn't prove it is read-only, so make only the writes he asked for.
- For a thread, call create-reply or create-reply-all, then update that draft and put your text inside the existing `<body>`, above the quoted thread. A new message won't join the thread.
- Put asides in brackets and names of endpoints or systems in italics (`<i>`), as he does: *(kanske)*, */dates*, *Brickz TEST*.
- Match his mail: Aptos 12pt, black. Use `<div>` lines with `<div><br></div>` between paragraphs and native `<ol>` or `<ul>` lists. Copy the style from a recent sent mail.
- Before updating a draft, read it again and keep every edit he made. After writing, read it back to check text, recipients and the quoted thread.
