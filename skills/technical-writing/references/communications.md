# Emails, messages, status updates, minutes and proposals

A message is read by someone deciding whether to act. Its first lines carry what you need from them; the rest
supports it. The audience rule of `SKILL.md` applies: a reference is fine only if the reader can resolve it.

## Every message: the bottom line first

1. **Opening**: the purpose in one sentence: the request, the decision you need or the news. With a deadline when
   there is one. Background comes after it, never before.
2. **What you need**: each ask with who, what and by when. Several questions are numbered, so the reply can
   answer them point by point.
3. **Context**: only what the reader needs to act on the ask.
4. **Close**: the next step, and what happens if there is no answer, when that matters.

One topic per message. Attachments are named in the text ("the attached contract, `rental-terms-v3.pdf`").

## Formal email to a partner, client or other external reader

- **Subject**: the action and the deadline: "Approval needed: rental terms v3 by 12 March". Not "Update" or
  "Rental terms".
- The body starts, right after the salutation, with the request and its deadline.
- **References the reader can resolve only**: no internal tracker keys, code names, internal hosts, colleagues the
  reader does not know, internal environment names. Describe the item, or link something they can open.
- Salutation, closing and form of address follow `register.md` (formal).

```text
Subject: Approval needed: rental terms v3 by 12 March

Dear Ms Okafor,

Could you approve the rental terms v3 by 12 March? Without approval by then, the fleet handover on 19 March
moves to April.

The attached rental-terms-v3.pdf changes three points from v2: ...

Questions for your team:
1. ...
2. ...
```

## Informal email or chat with colleagues

- One message, not a greeting followed by the content: "Hi Ana, can you review the pricing PR by 3 pm today? ...".
- Say the deadline and how urgent it is; say the fallback if they cannot ("if not, I'll ask Tom").
- Internal IDs, links and names are fine: colleagues can resolve them.
- Follow-ups go in the thread.
- No formal closing formulas.

## Status update (weekly report, project status)

1. **Status first**: on track, at risk or blocked, the reason in one sentence, and the change since the last update.
2. **Decisions needed**: each with the options, their consequences, the owner and the deadline. Omit the section
   when there is none.
3. **Done**, **Next**, **Risks**: short lists, outcomes rather than activities. Only what changed since the last
   update.

Never a day-by-day log: regroup the notes by topic and outcome.

## Meeting minutes

Date, attendees, then three sections: **Decisions** (what was decided), **Actions** (each with owner and due date),
**Open points** (with who follows up). Not a transcript of who said what. Send them the same day.

## Decision request / proposal (one-pager, RFC)

1. The decision asked, who decides, by when.
2. The context: the problem, in at most one paragraph.
3. The options: for each, what it gives, what it costs, its risks.
4. The recommendation and why.
5. What happens if no decision is taken by the deadline.

## Incident communication

Status page posts and customer notices during an incident: `operator-docs.md`.
