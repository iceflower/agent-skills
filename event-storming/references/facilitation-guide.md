# Event Storming Facilitation Guide

Detailed step-by-step guide for facilitating Event Storming workshops at each level.

## Pre-Workshop Checklist

### Materials (In-Person)

- [ ] Wide paper roll (minimum 1m × 10m) or large whiteboard wall
- [ ] Super-sticky notes in all standard colors (7.6cm × 7.6cm)
  - Orange (Domain Events) — need the most
  - Blue (Commands)
  - Large yellow (Aggregates)
  - Small yellow (Actors)
  - Green (Read Models)
  - Red/Hot Pink (Hot Spots)
  - Lilac/Purple (Policies)
  - Pink (External Systems)
- [ ] Fine-tip markers (0.8mm, one per participant)
- [ ] Flipchart markers for facilitator
- [ ] Masking tape
- [ ] Timer (phone or physical)
- [ ] Flipchart pad for decisions and action items
- [ ] Camera to photograph the board at the end

### Materials (Remote)

- [ ] Miro/MURAL board with Event Storming template
- [ ] Video conferencing with screen sharing
- [ ] Verify all participants have board edit access
- [ ] Prepare a "practice zone" on the board for warm-up
- [ ] Timer visible to all participants

### Room Setup (In-Person)

- Remove all chairs from the modeling area
- Place paper roll at eye level on the wall
- Prepare a "legend" area showing sticky color meanings
- Set up a separate area for parking lot / decisions
- Ensure good lighting and accessible refreshments

## Big Picture — Detailed Facilitation Script

### Phase 1: Opening (10-15 min)

```text
"Today we're going to explore our business domain together.
There are no wrong answers — we want to capture everything
that happens in our business. We'll use orange sticky notes
to write down events — things that have happened.
Write them in past tense. One event per sticky."
```

- Explain the goal: shared understanding, not final design
- Show the color legend
- Emphasize: everyone's perspective matters equally

### Phase 2: Warm-Up (20 min, optional)

Use a familiar process everyone understands:

- "How do you order a pizza online?" or "What happens when you book a flight?"
- Have participants write events on orange stickies
- Arrange on timeline together
- This builds confidence with the format before tackling the real domain

### Phase 3: Chaotic Exploration (25 min)

```text
"Now let's do the same for our actual domain. Write as many
domain events as you can think of. Don't worry about order
or completeness — just get everything on stickies."
```

- Set a timer
- Encourage volume over quality
- Walk around, answer questions quietly
- Resist the urge to organize during this phase

### Phase 4: Enforce Timeline (30-45 min)

```text
"Let's arrange these events in the order they happen.
Start from the left with early events, move right for later ones.
Duplicates are fine — we'll merge them."
```

- Facilitator starts by placing one clear "beginning" event
- Invite participants to place their stickies relative to existing ones
- Merge duplicates, discuss disagreements
- Look for "pivotal events" that change the direction of the flow

### Phase 5: Hot Spots (15-20 min)

```text
"Now let's mark areas where we have questions, disagreements,
or concerns with red stickies. These are Hot Spots."
```

- Walk the timeline left to right
- At each cluster, ask: "Does anyone have questions about this area?"
- Write specific questions, not vague concerns

### Phase 6: Enrich (30-45 min)

Add Actors (small yellow), External Systems (pink), and optionally Commands (blue):

- "Who or what triggers this event?"
- "Does this involve an external system?"
- Begin to see natural groupings emerge

### Phase 7: Boundaries (20-30 min)

- Step back and look at the entire board
- Draw lines where event flow naturally clusters
- Name each area with a pink sticky
- These become candidate Bounded Contexts

### Phase 8: Wrap-Up (30 min)

- Photograph the entire board
- Review Hot Spots — assign owners
- Agree on next steps (Process Modeling sessions, follow-up workshops)
- Thank participants

## Process Modeling — Key Differences

| Aspect | Big Picture | Process Modeling |
| --- | --- | --- |
| Scope | Entire domain | Single process |
| Start/End | Open-ended | Defined trigger and outcome |
| Elements | Mostly events | Events + Commands + Policies |
| Duration | 4-8 hours | 2-4 hours |

### Process Modeling Facilitation Tips

- Begin with the triggering event and the desired outcome
- Work forward from trigger: "What happens next?"
- Add Commands between events: "What action caused this?"
- Add Policies: "Is there an automated rule here?"
- Map External Systems: "Does this involve another system?"

## Design Level — Key Techniques

### Blank Aggregates Technique

This is Alberto Brandolini's approach to identifying Aggregates
without requiring participants to understand the DDD concept.

```text
Step 1: "For each Command → Event pair, what rules must be true?"
        Place a blank yellow sticky between Command and Event.

Step 2: "Write the business rules on separate stickies and attach
        them to the blank yellow."

Step 3: "Now group related rules together — rules that operate on
        the same data or enforce the same invariant."

Step 4: "Name each group. This name is your Aggregate."
```

### Read Model Sketching

For each Command, ask: "What information does the Actor need to see
to make this decision?"

- Sketch quick wireframe on green stickies or separate paper
- Focus on data needed, not UI design
- These become API contracts or view models

## Facilitation Anti-Patterns

| Pattern | Symptom | Fix |
| --- | --- | --- |
| **The Lecturer** | Facilitator talks more than participants | Ask questions, then stay silent |
| **The Perfectionist** | Constantly correcting stickies | Let the group self-correct |
| **The Timekeeper** | Rigidly cutting discussions | Flex timing based on energy |
| **The Absent Expert** | Key domain expert leaves early | Schedule around their availability |
| **The Solution Jumper** | Participants discuss implementation | "How does the business work today?" |
| **The Lonely Facilitator** | One facilitator for 15+ people | Co-facilitate with a partner |

## Post-Workshop Actions

1. **Digitize**: Photograph or screenshot the board, transcribe into a structured format
2. **Share**: Distribute results to all participants and stakeholders
3. **Prioritize Hot Spots**: Rank by business impact and assign owners
4. **Plan follow-ups**: Schedule Process Modeling or Design Level sessions
5. **Start implementing**: Don't wait for perfection — begin coding from the model
6. **Revisit**: Re-run workshops as understanding evolves

## Resources

- [EventStorming Official Site](https://www.eventstorming.com/)
- [Introducing EventStorming (Brandolini)](https://leanpub.com/introducing_eventstorming)
- [Event Storming Cheat Sheet](https://github.com/wwerner/event-storming-cheatsheet)
- [Miro Event Storming Template](https://miro.com/miroverse/event-storming/)
