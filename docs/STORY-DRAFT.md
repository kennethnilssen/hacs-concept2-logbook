---
owner: kennethnilssen
last-verified: 2026-11-15
---

# Story draft: text for Claude Code to write

This file is a work order, not a finished document. Use it, then delete it in the last commit.

## Instructions for Claude Code

1. Read `docs/WRITING-STANDARD.md` and `CLAUDE.md` first. Show a plan. Wait for approval.
2. Work on the branch `docs/story`. Make small `docs:` commits. Open a pull request. The
   owner merges.
3. Write **text A** into `README.md` as a new section `## Why this exists`, directly before
   `## Attribution`. Add a link to `docs/STORY.md` in the Attribution section.
4. Write **text B** to the new file `docs/STORY.md`, with the frontmatter shown in text B.
5. Use the words in the texts. You can shorten a sentence. Do not add a claim. Do not
   change a date or a number.
6. A line that starts with `CONFIRM:` is a claim that the owner has not confirmed. Do not
   write it. Ask the owner in the chat. Write the line only after he says yes. Remove the
   `CONFIRM:` marker when you write it.
7. Check each sentence against section 2 of the writing standard (20 and 25 words). The
   texts are in the first person on purpose. Keep the first person in these two places only.
8. Do not change the tagline, the attribution text, the licence, the code or the tests.
9. After the story is in, update open item 2 in the design document. The brand icon now
   exists (version 1.0.3). Keep the rest of that item.
10. Ask the owner if this documentation change needs a patch release (decision D11). Do
    not tag by yourself.
11. Run the checklist in section 7 of the writing standard. Delete this file in the last
    commit.

---

## Text A — README section

```markdown
## Why this exists

I row at home on a Concept2 rowing machine, and I run my home on Home Assistant.
My training results lived in one place and my home lived in another.

This integration connects the two. In my home, a button in the training room starts a
scene and speaks the distance of my previous result.

I built it as a personal, read-only project, and I share it as it is. Claude Code wrote
the code. I set the rules, reviewed every change and tested it on my own account.
The full story is in [docs/STORY.md](docs/STORY.md).
```

## Text B — `docs/STORY.md`

```markdown
---
owner: kennethnilssen
last-verified: 2026-11-15
---

# The story of this integration

This page tells why I built the integration, how I worked with Claude Code, and what went
wrong on the way. It is a personal account. The facts are in the
[design document](../concept2-ha-integration-design.md) and in the
[changelog](../CHANGELOG.md).

## Why I built it

I own a Concept2 rowing machine and I run my home on Home Assistant. I wanted my results
as sensors and as an event, so that a dashboard and an automation can use them.

I have worked in IT service management for more than 20 years. I judge a supplier by three
things: clear requirements, honest reporting and proof that the service works. I used the
same three things with an AI coding agent.

## The brief

The scope was small. I am the only user, the project is personal and the integration only
reads. Live data from the PM5 is out of scope, because other integrations provide it.

Before the first line of code, I wrote four constraints in `CLAUDE.md`:

- **C1:** the repository follows the HACS requirements.
- **C2:** the integration follows the Concept2 API documentation and terms.
- **C3:** the authentication is self-service and the user can revoke it.
- **C4:** the code is reviewable, the OWASP mapping stays true, and the repository states
  that Claude Code wrote it.

If a change broke one of them, Claude Code had to stop and report it.

## The method

I designed in a chat session and then gave Claude Code written briefs. The design document
has six gates, from the idea to the release. Claude Code did not start work from a later gate
without my approval.

I used the mode that asks permission for each change, so I approved every diff. The commits
are small. The tests travel with the code. CI runs ruff, hassfest, the HACS validation and
pytest. I recorded each design change as a numbered decision with a reason and a rejected
alternative.

## What went wrong

- **The wrong authentication.** The first version used OAuth2. On 2026-07-11 I replaced it
  with a personal access token. The OAuth registration is for apps with many users, and an
  individual sees only the token on the Concept2 profile page (decision D5).
- **A silent bug.** The event `concept2_new_result` could stay silent after a reload of the
  integration. A test on a real instance showed it. It is fixed.
- **An odd API response.** Concept2 sends the challenge response with the wrong content type
  and sends `{}` when no challenge exists. The integration now accepts both.
- **A release with open tests.** I tagged `v1.0.0` on 2026-07-12 while two manual tests were
  open. Both passed the same day. I wrote this in the design document and did not hide it
  (decision D6).

## What the four months showed

The first commit is dated 2026-07-05, and the first stable release is dated 2026-07-12.
From 2026-07-12 to 2026-11-15 the code did not change. Version 1.0.3 on 2026-11-15 added the
icon and removed unused constants.

CONFIRM: The integration ran on my own Home Assistant instance for the whole period, and I
did not have to fix it by hand.

In my home, a dashboard section shows the results, and a button in the training room
starts a scene and speaks the distance of my previous result.

## What I learned

1. **Write the constraints first.** They stop a bad change before it starts.
2. **Put gates between the idea and the code.** A gate gives a clear point to say stop.
3. **Test on the real service.** The mocks did not show the odd challenge response.
4. **Review every diff.** The agent writes fast. A person must still read the result.
5. **Write the limits where the user reads them.** The README says what I tested and what I
   did not test.

## Limits and next steps

I tested the integration on one account and one Home Assistant instance. Other people have
not tested it. It is not in the HACS default store.

Open decisions are in section 7 of the design document. Issues are welcome in the
[issue tracker](../../../issues).
```
