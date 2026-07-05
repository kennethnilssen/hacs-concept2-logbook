# Kickoff prompt — paste this as your first message in Claude Code

I'm building a Home Assistant HACS integration for the Concept2 Logbook.
This folder contains two documents you must read before anything else:

1. CLAUDE.md — the working agreement and binding constraints (C1–C4)
2. concept2-ha-integration-design.md — the full scope, solution design,
   sensor specification, and test plan, organized as a stage-gate model

Read both now, then:

1. Confirm your understanding of the scope and the four binding constraints
   in your own words.
2. Tell me if you see any conflicts, risks, or gaps in the design before we build.
3. Propose your Gate 3 build plan as an ordered task list matching design doc §5
   (scaffold + CI first, then API client with mocked tests, then OAuth config
   flow, then coordinator/sensors/events, then docs). Wait for my approval
   before writing any code.

Context you should know:
- I am new to Claude Code — explain what you're doing as we go.
- We develop against the Concept2 DEVELOPMENT server first (constraint C2).
  My API client credentials are NOT to be written into any file; they go into
  Home Assistant's Application Credentials UI at test time.
- My hardware is a RowErg PM5; my logbook account is new, so the first-sync
  experience must be tested with an empty/near-empty history.
- Initialize a git repository in this folder as the very first action if one
  doesn't exist yet.
