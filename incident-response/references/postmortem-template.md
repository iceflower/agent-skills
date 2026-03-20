# Postmortem Template

A structured template for incident postmortems with guidelines for conducting blameless reviews.

## Overview

A postmortem is a structured review conducted after an incident to understand what happened, why it happened, and how to prevent recurrence. The goal is organizational learning, not individual blame.

## Blameless Culture

### Core Principles

- **People did reasonable things** given the information they had at the time
- **Blame fixes nothing**: Punishing individuals discourages reporting and transparency
- **Systems enable errors**: Focus on what system conditions allowed the incident
- **Hindsight is not foresight**: Avoid judging past decisions with current knowledge

### Language Guide

| Blame-Oriented (Avoid)                    | Blameless (Use)                                |
| ----------------------------------------- | ---------------------------------------------- |
| "Engineer X caused the outage"            | "The deployment process allowed the change to reach production without catching the issue" |
| "The team failed to monitor"              | "The monitoring configuration did not cover this failure mode" |
| "Should have known better"                | "The documentation did not clearly indicate this risk" |
| "Careless mistake"                        | "The system allowed the misconfiguration to be applied" |

### Facilitator Responsibilities

- Redirect blame-oriented comments to systemic analysis
- Ensure all perspectives are heard
- Keep discussion focused on learning and prevention
- Document action items with clear owners and deadlines

## Postmortem Template

```text
# Incident Postmortem: [Title]

## Metadata
- Date of incident: [YYYY-MM-DD]
- Duration: [start time - end time, with timezone]
- Severity: [SEV-1/2/3/4]
- Incident commander: [Name]
- Postmortem author: [Name]
- Postmortem date: [YYYY-MM-DD]
- Status: [Draft / In Review / Complete]

---

## Executive Summary

[2-3 sentences describing what happened, the impact, and current status.
Written for a non-technical audience.]

---

## Impact

- Users affected: [number or percentage]
- Duration of user-facing impact: [duration]
- Revenue impact: [estimated amount or "none"]
- SLA impact: [which SLOs were violated, by how much]
- Data impact: [any data loss or corruption]
- Support tickets: [count of related tickets]

---

## Timeline

All times in [timezone].

| Time  | Event                                              |
| ----- | -------------------------------------------------- |
| 14:00 | Deployment of order-service v2.3.1 begins          |
| 14:05 | Deployment complete, canary shows normal metrics    |
| 14:15 | Error rate begins climbing (gradual)               |
| 14:25 | Alert: HighErrorRate fires for order-service        |
| 14:28 | On-call engineer acknowledges alert                 |
| 14:35 | Incident declared, SEV-2 assigned                   |
| 14:40 | Root cause identified: database connection pool exhaustion |
| 14:45 | Decision to rollback deployment                     |
| 14:50 | Rollback complete                                   |
| 14:55 | Error rate returns to normal                        |
| 15:00 | Incident resolved, monitoring continues             |

---

## Root Cause Analysis

### What Happened

[Detailed technical description of the failure chain.
Include diagrams if helpful.]

### Why It Happened

Use the "5 Whys" technique:

1. **Why** did the error rate increase?
   → Database connections were exhausted.

2. **Why** were connections exhausted?
   → New code path opened connections without using the connection pool.

3. **Why** did the code bypass the pool?
   → The new ORM integration used a different configuration path.

4. **Why** was this not caught in review?
   → The connection pool bypass was in a transitive dependency change.

5. **Why** was it not caught in testing?
   → Load tests did not exercise the new code path with production-like concurrency.

### Contributing Factors

- [Factor 1]: [Description]
- [Factor 2]: [Description]
- [Factor 3]: [Description]

---

## Detection

- How was the incident detected? [Alert / Customer report / Manual observation]
- Time from start to detection: [duration]
- Was detection timely? [Yes / No, with explanation]
- What monitoring gaps existed? [Description]

---

## Response

- Time from detection to response: [duration]
- Was the escalation process followed? [Yes / No]
- Were the right people involved? [Yes / No]
- What went well in the response? [List]
- What could improve in the response? [List]

---

## Action Items

| # | Action                                  | Type       | Priority | Owner  | Due Date   | Status |
| - | --------------------------------------- | ---------- | -------- | ------ | ---------- | ------ |
| 1 | Add connection pool validation to CI    | Prevention | P1       | [Name] | [Date]     | TODO   |
| 2 | Add load test for new code path         | Prevention | P1       | [Name] | [Date]     | TODO   |
| 3 | Add connection pool metrics to dashboard| Detection  | P2       | [Name] | [Date]     | TODO   |
| 4 | Update deployment canary to check DB metrics | Detection | P1  | [Name] | [Date]     | TODO   |
| 5 | Document ORM connection pool config     | Process    | P2       | [Name] | [Date]     | TODO   |

Action types:
- **Prevention**: Prevents this class of incident from recurring
- **Detection**: Improves detection speed for similar incidents
- **Mitigation**: Reduces impact when similar incidents occur
- **Process**: Improves response procedures

---

## Lessons Learned

### What Went Well
- [Positive observation 1]
- [Positive observation 2]

### What Went Poorly
- [Issue 1]
- [Issue 2]

### Where We Got Lucky
- [Lucky circumstance that reduced impact]

---

## Appendix

- [Link to incident channel logs]
- [Link to relevant dashboards]
- [Link to deployment diff]
- [Related past incidents]
```

## Postmortem Process

### Scheduling

| Severity | Postmortem Required | Timeline              |
| -------- | ------------------- | --------------------- |
| SEV-1    | Yes (mandatory)     | Within 3 business days|
| SEV-2    | Yes (mandatory)     | Within 5 business days|
| SEV-3    | Optional            | Within 2 weeks        |
| SEV-4    | No                  | N/A                   |

### Review Meeting Agenda

```text
Duration: 60 minutes

1. (5 min)  Set ground rules (blameless)
2. (10 min) Walk through timeline
3. (15 min) Root cause analysis discussion
4. (10 min) Detection and response review
5. (15 min) Action items: define, prioritize, assign owners
6. (5 min)  Lessons learned, closing
```

### Follow-Up

- Action items tracked in issue tracker with `postmortem` label
- Review action item progress in next team meeting
- Close postmortem only when all P1 action items are complete
- Share postmortem with broader engineering organization for learning
