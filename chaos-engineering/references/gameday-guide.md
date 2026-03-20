# Gameday Guide

A structured approach to planning, executing, and analyzing chaos engineering gamedays.

## Overview

A Gameday is a planned event where teams deliberately inject failures into systems to discover weaknesses, validate resilience, and build operational confidence. Unlike ad-hoc chaos experiments, gamedays are organized events with clear objectives, defined scope, and structured follow-up.

## Planning Phase

### Timeline

```text
4 weeks before:  Define objectives and scope
3 weeks before:  Design experiments and hypotheses
2 weeks before:  Review with stakeholders, get approval
1 week before:   Prepare monitoring, runbooks, rollback plans
Day of:          Execute gameday
1 week after:    Complete analysis and action items
```

### Defining Objectives

Every gameday needs clear, measurable objectives:

| Objective Type          | Example                                                |
| ----------------------- | ------------------------------------------------------ |
| Validate resilience     | "Order service recovers within 30s of database failover"|
| Test detection          | "Alert fires within 2 minutes of payment service outage"|
| Verify runbooks         | "On-call can restore service using documented runbook"  |
| Build confidence        | "System handles 3x traffic spike without degradation"   |
| Train team              | "New team members practice incident response"           |

### Hypothesis Template

```text
Hypothesis: [System behavior under normal conditions]
Experiment: [Fault to inject]
Expected: [What we expect to happen]
Abort if: [Conditions that require immediate halt]
```

**Example**:

```text
Hypothesis: The order service maintains availability when the payment service is down
Experiment: Kill all payment service pods for 5 minutes
Expected: Orders are accepted and queued; payment processing resumes automatically
         Error rate stays below 1%; latency increases by < 500ms
Abort if: Order error rate exceeds 10% OR data loss is detected
```

### Scope Definition

```text
┌─────────────────────────────────────────────┐
│              Blast Radius                    │
│                                              │
│  In Scope:                                   │
│  ✓ Order service (production, region: us-east)│
│  ✓ Payment service dependency                │
│  ✓ Database failover                         │
│                                              │
│  Out of Scope:                               │
│  ✗ User authentication system                │
│  ✗ Other regions                             │
│  ✗ Third-party integrations                  │
└─────────────────────────────────────────────┘
```

### Approval Checklist

- [ ] Objectives documented and reviewed
- [ ] Hypotheses written for each experiment
- [ ] Blast radius defined and limited
- [ ] Rollback plan verified
- [ ] Monitoring dashboards prepared
- [ ] Stakeholders notified (SRE, product, support)
- [ ] Customer impact assessment completed
- [ ] Abort criteria defined for each experiment
- [ ] On-call team briefed and available

## Execution Phase

### Roles

| Role               | Responsibility                                    |
| ------------------ | ------------------------------------------------- |
| Gameday Lead       | Coordinates execution, makes go/no-go decisions   |
| Experiment Runner  | Executes fault injection                          |
| Observer           | Monitors dashboards and system behavior           |
| Scribe             | Documents timeline, observations, findings        |
| Safety Officer     | Watches abort criteria, triggers halt if needed   |

### Execution Sequence

```text
1. PRE-FLIGHT
   ├── Verify system is in steady state
   ├── Confirm all participants are ready
   ├── Open monitoring dashboards
   └── Start recording timeline

2. INJECT FAULT
   ├── Announce experiment start
   ├── Inject fault using chaos tool
   ├── Start timer
   └── Record injection timestamp

3. OBSERVE
   ├── Monitor system metrics
   ├── Check alert firing
   ├── Verify user-facing impact
   ├── Note any unexpected behaviors
   └── Document observations in real time

4. RECOVER
   ├── Remove fault (or let duration expire)
   ├── Verify system returns to steady state
   ├── Record recovery time
   └── Note any recovery anomalies

5. COOL DOWN
   ├── Wait for full stabilization
   ├── Verify no lingering effects
   └── Proceed to next experiment or wrap up
```

### Communication Template

```text
[START] Gameday Experiment #1 starting now
  Target: order-service pods in us-east
  Fault: Kill 2 of 3 pods
  Duration: 5 minutes
  Expected: Auto-scaling replaces pods within 60s

[OBSERVATION] T+30s: 1 pod terminated, HPA scaling triggered
[OBSERVATION] T+60s: New pod starting, requests routing to remaining pod
[OBSERVATION] T+90s: Second pod terminated, brief latency spike (p99: 2.1s)
[ALERT] T+120s: HighLatency alert fired (expected)
[OBSERVATION] T+180s: Both replacement pods healthy, traffic normalized

[END] Experiment #1 complete. Recovering to steady state.
  Result: PARTIAL MATCH - recovery took 180s (expected 60s)
```

### Abort Criteria

Stop the experiment immediately if:

- Data corruption is detected
- Error rate exceeds defined threshold
- Customer-facing outage beyond acceptable duration
- Unexpected cascade to out-of-scope systems
- Safety officer calls halt for any reason

```bash
# Emergency stop commands
kubectl delete podchaos pod-kill-test -n chaos-mesh
kubectl delete chaosengine order-service-chaos -n production
```

## Post-Analysis Phase

### Analysis Framework

```text
For each experiment:
  1. Did the result match the hypothesis?
     ├── YES: Document as validated resilience
     └── NO: Classify as finding

  2. For each finding:
     ├── What happened?
     ├── Why did it happen?
     ├── What is the impact?
     └── What should we do about it?

  3. Prioritize actions:
     ├── P0: Fix before next deployment
     ├── P1: Fix within current sprint
     ├── P2: Add to backlog
     └── Accepted risk: Document rationale
```

### Gameday Report Template

```text
# Gameday Report: [Title]
Date: [YYYY-MM-DD]
Participants: [Names and roles]

## Objectives
- [Objective 1]: [Met / Partially Met / Not Met]
- [Objective 2]: [Met / Partially Met / Not Met]

## Experiment Results Summary

| # | Experiment         | Hypothesis | Result         | Finding |
|---|-------------------|------------|----------------|---------|
| 1 | Pod kill          | Recovery < 60s | Recovery: 180s | Yes  |
| 2 | Network partition | Graceful degradation | As expected | No  |
| 3 | DB failover       | Auto-failover | Manual intervention needed | Yes |

## Key Findings

### Finding 1: Slow pod recovery
- **Observed**: Pod recovery took 180s instead of expected 60s
- **Root cause**: HPA scaling threshold too conservative
- **Impact**: Extended latency during pod failures
- **Action**: Adjust HPA min replicas from 2 to 3 (P1)
- **Owner**: [Name]

## Action Items
| # | Action                        | Priority | Owner  | Due Date   |
|---|-------------------------------|----------|--------|------------|
| 1 | Adjust HPA min replicas       | P1       | [Name] | [Date]     |
| 2 | Add DB failover to runbook    | P1       | [Name] | [Date]     |
| 3 | Update alerting thresholds    | P2       | [Name] | [Date]     |

## Lessons Learned
- [Key takeaway 1]
- [Key takeaway 2]
```

## Gameday Cadence

| Team Maturity      | Recommended Frequency | Scope                |
| ------------------ | --------------------- | -------------------- |
| Beginning          | Quarterly             | Staging only         |
| Intermediate       | Monthly               | Staging + limited prod |
| Advanced           | Weekly (automated)    | Production           |

Start in staging with simple experiments. Graduate to production as confidence grows.
