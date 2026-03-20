---
name: incident-response
description: >-
  Incident response workflow including severity classification, communication
  protocols, triage, mitigation strategies, runbook authoring, postmortem
  process, and on-call best practices. Covers MTTD, MTTA, MTTR metrics
  and SLO/SLI/SLA relationships.
  Use when handling production incidents, writing runbooks, or establishing
  incident response procedures.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility:
  - OpenCode
  - Claude Code
  - Codex
  - Antigravity
---

# Incident Response Rules

## 1. Severity Classification

### Severity Levels

| Level | Name | Definition | Response Time | Update Cadence |
| --- | --- | --- | --- | --- |
| SEV1 | Critical | Service-wide outage, data loss, security breach | 15 min | Every 15 min |
| SEV2 | Major | Significant feature degraded, partial outage | 30 min | Every 30 min |
| SEV3 | Minor | Minor feature degraded, workaround available | 4 hours | Every 2 hours |
| SEV4 | Low | Cosmetic issue, no user impact | Next business day | On resolution |

### Severity Examples

| Scenario | Severity |
| --- | --- |
| All users cannot log in | SEV1 |
| Payment processing failing for 30% of transactions | SEV1 |
| Search results returning stale data | SEV2 |
| Dashboard loading slowly (>10s) | SEV2 |
| CSV export timing out for large datasets | SEV3 |
| Tooltip displaying wrong timezone | SEV4 |

### Escalation Path

```text
SEV1: On-call → Team Lead → Engineering Manager → VP Eng (within 30 min)
SEV2: On-call → Team Lead → Engineering Manager (within 1 hour)
SEV3: On-call → Team Lead (within 4 hours)
SEV4: Ticket in backlog
```

---

## 2. Incident Lifecycle

### Phases

```text
Detection → Triage → Mitigation → Resolution → Postmortem
    │          │          │            │            │
    ▼          ▼          ▼            ▼            ▼
  Alert     Assess     Stop the    Fix root     Learn and
  fires     impact     bleeding    cause        improve
```

### Role Assignments

| Role | Responsibility |
| --- | --- |
| Incident Commander (IC) | Owns the incident, coordinates response, makes decisions |
| Communications Lead | Updates stakeholders, status page, internal channels |
| Technical Lead | Leads investigation and mitigation efforts |
| Scribe | Documents timeline, decisions, and actions in real-time |

### Role Assignment Rules

- IC is the first responder until explicitly handed off
- For SEV1/SEV2, assign all four roles within 15 minutes
- IC should NOT be debugging — they coordinate
- Rotate IC during long incidents (>4 hours)

---

## 3. Communication Protocol

### Status Update Template

```text
[Incident #1234] [SEV1] [UPDATE 3] [2024-01-15 14:30 UTC]

Status: MITIGATING
Impact: 100% of users unable to complete checkout
Root cause: Database connection pool exhausted due to connection leak
Mitigation: Rolling restart of affected services in progress
ETA: 15 minutes to full recovery
Next update: 14:45 UTC
```

### Stakeholder Notification Matrix

| Severity | Engineering Team | Engineering Manager | Product Manager | Executive | External (Status Page) |
| --- | --- | --- | --- | --- | --- |
| SEV1 | Immediate | Immediate | Immediate | Within 30 min | Within 15 min |
| SEV2 | Immediate | Within 30 min | Within 1 hour | If >2 hours | If user-facing |
| SEV3 | Within 4 hours | Daily summary | Daily summary | No | No |
| SEV4 | Ticket created | No | No | No | No |

### Communication Channels

| Channel | Purpose |
| --- | --- |
| Incident Slack channel | Real-time coordination (create per SEV1/SEV2 incident) |
| Status page | External user communication |
| Email | Executive and stakeholder updates |
| War room (video call) | SEV1 coordination when needed |

---

## 4. Triage Checklist

### Initial Assessment (First 5 Minutes)

1. **What is broken?** — Identify the affected service/feature
2. **Who is affected?** — Estimate user impact (all users, specific region, specific plan)
3. **When did it start?** — Check monitoring for the onset time
4. **What changed?** — Review recent deployments, config changes, infrastructure events
5. **Is it getting worse?** — Check if error rate is increasing or stable

### Blast Radius Estimation

| Factor | Questions |
| --- | --- |
| Users affected | What percentage? All or specific segment? |
| Revenue impact | Is payment/checkout/billing affected? |
| Data integrity | Is data being corrupted or lost? |
| Cascading risk | Are other services at risk? |
| Security exposure | Is sensitive data exposed? |

### Quick Diagnostic Commands

```bash
# Check recent deployments
kubectl rollout history deployment/<app> -n <namespace>

# Check pod health
kubectl get pods -n <namespace> -o wide | grep -v Running

# Check recent logs for errors
kubectl logs -n <namespace> -l app=<app> --since=10m | grep -i error | tail -20

# Check resource pressure
kubectl top pods -n <namespace>

# Check events
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -20
```

---

## 5. Mitigation Strategies

### Decision Tree

```text
Is the issue caused by a recent deployment?
├── Yes → Rollback deployment
│         └── Still broken? → Check config changes
└── No
    ├── Is traffic volume abnormal?
    │   ├── Yes → Scale up / enable rate limiting
    │   └── No → Continue investigation
    ├── Is a dependency down?
    │   ├── Yes → Enable circuit breaker / failover
    │   └── No → Continue investigation
    └── Is data corrupted?
        ├── Yes → Stop writes, assess damage, plan recovery
        └── No → Deep investigation needed
```

### Mitigation Techniques

| Technique | When to Use | Command/Action |
| --- | --- | --- |
| Deployment rollback | Bad code deployed | `kubectl rollout undo deployment/<app>` |
| Feature flag kill switch | Feature-specific issue | Disable flag in feature management system |
| Traffic shifting | Partial failure | Route traffic to healthy instances/regions |
| Horizontal scaling | Capacity issue | `kubectl scale deployment/<app> --replicas=N` |
| Circuit breaker | Dependency failure | Enable circuit breaker for failing dependency |
| Rate limiting | Traffic spike/abuse | Tighten rate limits at ingress or API gateway |
| DNS failover | Zone/region failure | Update DNS to healthy region |
| Database rollback | Bad migration | Restore from backup or run rollback script |

### Mitigation Rules

- Prefer reversible actions (rollback, feature flag) over forward fixes during active incidents
- Communicate mitigation actions before executing them
- Document every action taken with timestamps
- If mitigation does not work within 15 minutes, escalate

---

## 6. Runbook Authoring

### Runbook Template

```markdown
# Runbook: [Service] — [Scenario]

## Overview
- **Service**: [service name]
- **Alert**: [alert name that triggers this runbook]
- **Severity**: [typical severity]
- **Last updated**: [date]
- **Owner**: [team name]

## Prerequisites
- [ ] Access to [environment/tool]
- [ ] Permissions: [required roles]

## Diagnosis Steps
1. Check [metric/dashboard] at [URL]
2. Run: `[diagnostic command]`
3. Expected output: [description]
4. If [condition], proceed to Mitigation A
5. If [other condition], proceed to Mitigation B

## Mitigation A: [Name]
1. Run: `[command]`
2. Verify: `[verification command]`
3. Expected result: [description]

## Mitigation B: [Name]
1. Run: `[command]`
2. Verify: `[verification command]`

## Escalation
- If neither mitigation works within [time], escalate to [team/person]
- Contact: [escalation contact info]

## Post-Mitigation Verification
1. Confirm error rate returns to baseline
2. Confirm no data loss or corruption
3. Monitor for [time period] before declaring resolved
```

### Runbook Rules

- Every SEV1-capable alert MUST have a linked runbook
- Runbooks must be tested quarterly (dry run)
- Include exact commands, not vague instructions
- Include verification steps after each action
- Link to relevant dashboards and documentation

---

## 7. Postmortem Process

### Timing

| Severity | Postmortem Required | Deadline |
| --- | --- | --- |
| SEV1 | Yes | Within 3 business days |
| SEV2 | Yes | Within 5 business days |
| SEV3 | Optional | Within 2 weeks |
| SEV4 | No | — |

### Blameless Postmortem Template

```markdown
# Postmortem: [Incident Title]

## Metadata
- **Incident #**: [ID]
- **Date**: [YYYY-MM-DD]
- **Duration**: [start — end, total duration]
- **Severity**: [SEV level]
- **Author**: [name]
- **Reviewers**: [names]

## Summary
[2-3 sentence summary of what happened and the impact]

## Impact
- **Users affected**: [number/percentage]
- **Revenue impact**: [if applicable]
- **Data impact**: [if applicable]
- **Duration**: [time from detection to resolution]

## Timeline (all times UTC)
| Time | Event |
| --- | --- |
| 09:00 | Deployment X rolled out |
| 09:15 | Alert fired: error rate >5% |
| 09:18 | IC assigned, triage started |
| 09:25 | Root cause identified: connection leak |
| 09:30 | Rollback initiated |
| 09:35 | Error rate returning to baseline |
| 09:45 | Incident resolved |

## Root Cause
[Detailed technical explanation of what went wrong and why]

## Detection
- How was the incident detected? [alert / user report / manual check]
- Could we have detected it sooner? [yes/no, explain]

## Resolution
[What actions were taken to resolve the incident]

## Lessons Learned
### What went well
- [item]

### What went poorly
- [item]

### Where we got lucky
- [item]

## Action Items
| Action | Owner | Priority | Deadline | Ticket |
| --- | --- | --- | --- | --- |
| Add connection pool monitoring | @engineer | P1 | 2024-01-22 | JIRA-123 |
| Update runbook with new scenario | @oncall | P2 | 2024-01-29 | JIRA-124 |
```

### Root Cause Analysis Techniques

| Technique | When to Use |
| --- | --- |
| 5 Whys | Simple causal chains |
| Fishbone (Ishikawa) | Multiple contributing factors |
| Fault Tree Analysis | Complex system failures with multiple paths |
| Timeline Analysis | Time-sensitive cascading failures |

### Postmortem Rules

- MUST be blameless — focus on systems, not individuals
- All action items must have owners and deadlines
- Review action items in the next sprint/iteration
- Share postmortem with the broader engineering team
- Track recurring root causes to identify systemic issues

---

## 8. On-Call Best Practices

### Rotation Design

| Element | Recommendation |
| --- | --- |
| Rotation length | 1 week (handoff on weekday mornings) |
| Team size | Minimum 4-5 people per rotation |
| Shadow on-call | Pair new team members for 1-2 rotations |
| Compensation | Follow company policy (time off, pay premium) |
| Handoff | Sync meeting: open incidents, recent changes, known risks |

### Alert Fatigue Reduction

- Review alert signal-to-noise ratio monthly
- Suppress alerts during planned maintenance windows
- Group related alerts to reduce notification volume
- Set appropriate thresholds — avoid alerting on transient spikes
- Every alert must be actionable — if no action needed, remove it
- Target: <5 pages per on-call shift (excluding false positives)

### Escalation Policy

```text
Level 1: Primary on-call (immediate)
Level 2: Secondary on-call (after 15 min no-ack)
Level 3: Team lead (after 30 min no-ack)
Level 4: Engineering manager (after 45 min no-ack)
```

---

## 9. Metrics and KPIs

### Key Incident Metrics

| Metric | Definition | Target |
| --- | --- | --- |
| MTTD (Mean Time to Detect) | Time from issue start to alert firing | <5 min |
| MTTA (Mean Time to Acknowledge) | Time from alert to first responder | <5 min |
| MTTR (Mean Time to Resolve) | Time from detection to resolution | <1 hour (SEV1) |
| MTTF (Mean Time to Failure) | Time between incidents | Increasing trend |
| Change Failure Rate | % of deployments causing incidents | <5% |

### SLO / SLI / SLA Relationships

| Concept | Definition | Example |
| --- | --- | --- |
| SLI (Indicator) | Measurable metric | Request success rate: 99.95% |
| SLO (Objective) | Internal target for SLI | Availability ≥ 99.9% per month |
| SLA (Agreement) | External contractual commitment | 99.5% uptime with penalty clause |

- SLO should be stricter than SLA — internal buffer
- Error budget = 1 - SLO (e.g., 0.1% = 43.2 min/month downtime budget)
- When error budget is exhausted, freeze non-critical deployments

---

## 10. Anti-Patterns

- Blaming individuals in postmortems — destroys psychological safety
- No runbooks for critical alerts — responders waste time investigating from scratch
- Skipping postmortems for SEV1/SEV2 — same incidents will recur
- IC also debugging — coordination suffers, nobody has the full picture
- Alerting on symptoms without context — responders cannot triage quickly
- Not tracking action items from postmortems — lessons are not learned
- Over-escalating every issue to SEV1 — severity inflation erodes urgency
- No handoff documentation between on-call shifts — context is lost
- Deploying during active incidents — adds more variables to troubleshoot
- No regular gameday drills — team discovers process gaps during real incidents

## Related Skills

- For secret leakage incidents and credential rotation procedures, see [secrets-management](../secrets-management/) skill
- For general debugging and diagnosis patterns, see [troubleshooting](../troubleshooting/) skill
- For chaos engineering and gameday practices, see [chaos-engineering](../chaos-engineering/) skill
