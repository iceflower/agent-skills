---
name: event-storming
description: >-
  Event Storming workshop facilitation guide including sticky note color
  conventions, workshop levels (Big Picture, Process Modeling, Design Level),
  facilitation techniques, DDD transition patterns (Bounded Context and
  Aggregate identification), remote Event Storming, and common pitfalls.
  Use when planning or facilitating Event Storming workshops, transitioning
  workshop results into domain models, or guiding teams through collaborative
  domain exploration.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
---

# Event Storming Rules

## 1. Overview

Event Storming is a workshop-based technique created by Alberto Brandolini for
collaboratively exploring complex business domains using sticky notes on a
wide modeling surface.

### Goals

- Build shared understanding of the business domain across all stakeholders
- Break silos between departments (business, development, design)
- Discover domain events, processes, pain points, and boundaries
- Transition workshop results into software architecture (DDD)

### Participants

- Domain experts (business stakeholders) — **essential**
- Developers and architects
- UX designers, product managers
- Ideal size: 6-8 people (Big Picture can handle 10-20+)

## 2. Sticky Note Color Conventions

| Color | Element | Description | Naming Convention |
| --- | --- | --- | --- |
| Orange | Domain Event | Something that happened in the domain | Past tense: `OrderPlaced` |
| Blue | Command | Intentional action triggering an event | Imperative: `PlaceOrder` |
| Yellow (large) | Aggregate | Domain object cluster that handles commands | Noun: `Order` |
| Yellow (small) | Actor / User | Person or role executing a command | Role: `Customer`, `Admin` |
| Green | Read Model / View | Data the actor sees to make decisions | Screen or data description |
| Red / Hot Pink | Hot Spot | Questions, concerns, unresolved issues | Question or problem statement |
| Lilac / Purple | Policy | Automation rule: "Whenever X, then Y" | `Whenever OrderPlaced, ReserveInventory` |
| Pink | External System | System outside the domain boundary | System name: `PaymentGateway` |

### Visual Flow (Design Level)

```text
[Actor] → [Command] → [Aggregate] → [Domain Event] → [Policy] → [Command] ...
              ↑                                            ↓
         [Read Model]                              [External System]

                         [Hot Spot]
```

## 3. Workshop Levels

### Big Picture

**Goal**: Macro-level understanding of the entire business domain.

| Aspect | Detail |
| --- | --- |
| Participants | 6-20+, diverse departments |
| Duration | 4-8 hours (half to full day) |
| Focus | Domain events, timeline, boundaries |

**Agenda:**

1. Introduction and goal alignment (10-15 min)
2. Optional warm-up with familiar process (20 min)
3. Chaotic exploration — freely generate domain events (25 min)
4. Enforce timeline — arrange events chronologically (30-45 min)
5. Mark Hot Spots — questions, conflicts, unknowns (15-20 min)
6. Add External Systems and Actors
7. Draw Bounded Context boundaries
8. Wrap-up and agree on next steps (30 min)

### Process Modeling

**Goal**: Detailed design of a specific business process.

| Aspect | Detail |
| --- | --- |
| Participants | 4-8, process domain experts |
| Duration | 2-4 hours |
| Focus | Commands, Policies, External Systems within one process |
| Prerequisite | Big Picture completed for this area |

### Design Level

**Goal**: Detailed model translatable 1:1 into code.

| Aspect | Detail |
| --- | --- |
| Participants | Primarily developers |
| Duration | 2-4 hours |
| Focus | Aggregates, business rules, read models, UI mockups |

**Steps:**

1. Set goal for the session
2. Identify Domain Events
3. Add Commands
4. Determine Actors and Policies
5. Place empty Read Model stickies
6. Sketch Read Model / UX mockups
7. Map External Systems
8. Place empty Business Rule stickies (Blank Aggregates technique)
9. Write business rules (invariants, pre/post conditions)
10. Group business rules by Aggregate
11. Name each Aggregate

For the detailed facilitation guide, see
[references/facilitation-guide.md](references/facilitation-guide.md).

## 4. Facilitation Techniques

### Preparation

- **Modeling space**: Minimum 1m × 10m paper roll or wide wall
- **Materials**: Colored sticky notes (7.6cm × 7.6cm, super-sticky), fine markers (0.8mm), masking tape
- **No chairs**: "Seats are poisonous" — standing maximizes engagement
- **Clear goal**: Define what the workshop should achieve before starting

### Time Management

- Set timers for each phase (can extend, but limits maintain flow)
- Alternate 10-15 min silent ideation with facilitator-led merging
- Reserve the last 30 minutes for Hot Spot review and action items

### Engagement

- Ask open questions, allow silence (invite, don't force participation)
- Approach quiet participants individually to re-explain instructions
- Create urgency: "We'll review in 10 minutes"
- If one person dominates, split the group to work on separate board sections

### Quality Control

- Rotate low-quality stickies 45° to flag them for rewriting
- Record decisions on a separate flipchart for tracking
- Proactively expand modeling space before it runs out

### Conflict Resolution

- Do not chase excessive consensus (prevents groupthink)
- Mark disagreements as Hot Spots (red stickies) and move on
- Resolve in dedicated follow-up sessions

## 5. Transition to DDD

### Bounded Context Identification

- Event flow in Big Picture naturally reveals domain boundaries
- Use "Functional Area" instead of "Bounded Context" for accessibility
- Draw boundaries with solid lines after understanding forms (never prematurely)
- Name each context with a pink sticky

### Aggregate Identification (Blank Aggregates Technique)

1. Do NOT ask participants to identify Aggregates directly
2. Place blank stickies and ask for business rules (invariants, constraints)
3. Let developers naturally group rules "as they would in code"
4. Grouped clusters become Aggregates — name them last

### Next Steps After Workshop

- Start implementation using identified Aggregates and Events
- Use Example Mapping for deeper business rule analysis
- Draw a Context Map to define relationships between Bounded Contexts (Partnership, Customer-Supplier, Conformist, ACL, etc.)
- For DDD tactical patterns, see the [ddd skill](../ddd/SKILL.md)

## 6. Remote Event Storming

### Recommended Tools

| Tool | Strengths |
| --- | --- |
| Miro | Infinite canvas, Event Storming templates, voting/timer |
| MURAL | Similar collaborative canvas, good for large teams |
| FigJam | Cursor chat, emoji reactions, good for small teams |

### Remote Best Practices

- **Short cycles**: 10-15 min silent ideation → facilitator-led merge, repeat
- **Verify access**: Confirm board access for all participants before the session
- **Cameras on**: 90% of Event Storming is collaboration, 60% is non-verbal
- **Dual screen**: Facilitator uses one for the board, one for video chat
- **Personal zones**: Draw vertical lines to separate personal work area (left) from shared timeline (right)
- **Co-facilitation**: Use two facilitators for remote sessions
- **Sign stickies**: Participants initial their notes for accountability

## 7. Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
| --- | --- | --- |
| Facilitator talks more than participants | Suppressed collaboration | Ask questions, then stay silent |
| No domain experts | Incomplete domain understanding | Always include business stakeholders |
| Premature detail | Lost in data attributes and validation | Stay at process level first |
| Events only | Superficial model without behavior | Add Commands, Policies, Aggregates |
| Big Design Up Front | Workshop becomes waterfall planning | Time-box; implement early, iterate |
| Treating output as final design | Rigid model that doesn't evolve | Output is a living model, not a spec |
| Early boundary drawing | Fragmented design without full context | Draw boundaries after understanding |
| Chasing consensus | Groupthink, suppressed diversity | Use Hot Spots for disagreements |
| No follow-up | Workshop results go unused | Plan implementation and follow-up sessions |
| Custom sticky colors | Confusion about conventions | Stick to the standard color scheme |
| Single session | Incomplete exploration | Plan 2-4 sessions for a new domain, more for complex domains |
