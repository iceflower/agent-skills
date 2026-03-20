# Severity Classification

Standardized severity levels, escalation criteria, and response expectations for incident management.

## Overview

Severity classification ensures consistent incident prioritization across teams. Clear definitions reduce ambiguity during high-pressure situations and set expectations for response times and communication cadence.

## Severity Levels

### SEV-1: Critical

**Definition**: Complete service outage or severe degradation affecting all users.

| Attribute              | Requirement                                     |
| ---------------------- | ----------------------------------------------- |
| User impact            | All or majority of users affected               |
| Revenue impact         | Direct, significant revenue loss                |
| Data impact            | Data loss or corruption possible                |
| Response time          | Immediate (< 5 minutes)                         |
| Update frequency       | Every 15 minutes                                |
| Communication          | Exec notification, status page, customer comms  |
| Responders             | Incident commander + all required engineers      |

**Examples**:

- Complete production outage
- Payment processing failure
- Data breach or security compromise
- Database corruption affecting production data

### SEV-2: High

**Definition**: Major feature degraded or unavailable, significant user impact.

| Attribute              | Requirement                                     |
| ---------------------- | ----------------------------------------------- |
| User impact            | Large subset of users or critical functionality  |
| Revenue impact         | Potential revenue impact                        |
| Data impact            | No data loss, possible inconsistency            |
| Response time          | < 15 minutes                                    |
| Update frequency       | Every 30 minutes                                |
| Communication          | Team leads notified, status page if external    |
| Responders             | On-call engineer + backup                       |

**Examples**:

- Core API returning errors for 20%+ of requests
- Search functionality completely down
- Significant performance degradation (5x normal latency)
- Authentication service intermittent failures

### SEV-3: Moderate

**Definition**: Minor feature degraded, workaround available, limited user impact.

| Attribute              | Requirement                                     |
| ---------------------- | ----------------------------------------------- |
| User impact            | Small subset of users or non-critical feature    |
| Revenue impact         | Minimal or none                                 |
| Data impact            | None                                            |
| Response time          | < 1 hour (business hours)                       |
| Update frequency       | Every 2 hours                                   |
| Communication          | Team channel notification                       |
| Responders             | On-call engineer                                |

**Examples**:

- Non-critical API endpoint returning errors
- Report generation delayed
- UI cosmetic issues affecting usability
- Monitoring gaps discovered (no immediate impact)

### SEV-4: Low

**Definition**: Minor issue with no significant user impact.

| Attribute              | Requirement                                     |
| ---------------------- | ----------------------------------------------- |
| User impact            | Negligible or internal only                     |
| Revenue impact         | None                                            |
| Data impact            | None                                            |
| Response time          | Next business day                               |
| Update frequency       | Daily                                           |
| Communication          | Ticket created                                  |
| Responders             | Assigned engineer                               |

**Examples**:

- Internal tool minor malfunction
- Non-critical log errors increasing
- Staging environment issues
- Documentation inaccuracies

## Escalation Criteria

### Automatic Escalation

```text
SEV-3 → SEV-2:
  - Duration exceeds 2 hours without resolution
  - User impact increases beyond initial assessment
  - Workaround stops functioning

SEV-2 → SEV-1:
  - Duration exceeds 1 hour without resolution
  - Additional critical systems affected (cascade)
  - Data integrity concerns emerge
  - Customer-reported impact exceeds initial scope
```

### Escalation Decision Tree

```text
Is the service completely down?
├── YES → SEV-1
└── NO
    ├── Is a core feature degraded for many users?
    │   ├── YES → SEV-2
    │   └── NO
    │       ├── Is a non-core feature affected with workaround?
    │       │   ├── YES → SEV-3
    │       │   └── NO → SEV-4
    │       └── Is there potential for escalation?
    │           ├── YES → SEV-3 (monitor closely)
    │           └── NO → SEV-4
    └── Is there data loss or security concern?
        └── YES → SEV-1 (regardless of user count)
```

## Response Structure

### Incident Roles

| Role                | SEV-1 | SEV-2 | SEV-3 | SEV-4 |
| ------------------- | ----- | ----- | ----- | ----- |
| Incident Commander  | Yes   | Yes   | No    | No    |
| Communications Lead | Yes   | Optional | No | No    |
| Technical Lead      | Yes   | Yes   | Yes   | No    |
| Scribe              | Yes   | Optional | No | No    |
| Subject Experts     | As needed | As needed | No | No |

### Communication Channels

```text
SEV-1:
  - Dedicated war room (video call)
  - Incident Slack channel: #inc-[date]-[short-desc]
  - Status page update within 10 minutes
  - Executive notification within 15 minutes

SEV-2:
  - Incident Slack channel
  - Status page update if customer-facing
  - Team lead notification

SEV-3:
  - Team Slack channel thread
  - Ticket update

SEV-4:
  - Ticket only
```

## Impact Assessment Checklist

When classifying severity, evaluate these dimensions:

- [ ] **Users affected**: How many? Which segments?
- [ ] **Functionality impact**: Core vs non-core feature?
- [ ] **Revenue impact**: Direct financial loss?
- [ ] **Data integrity**: Any risk of data loss or corruption?
- [ ] **Security**: Any security implications?
- [ ] **Blast radius**: Could this spread to other systems?
- [ ] **Workaround**: Is there an alternative path for users?
- [ ] **Duration**: How long has this been happening?
- [ ] **Trend**: Is the situation improving or worsening?

## Severity vs Priority

Severity and priority are distinct:

| Concept   | Definition                          | Set By              |
| --------- | ----------------------------------- | ------------------- |
| Severity  | Objective impact on users/business  | Incident responders |
| Priority  | Order of work relative to other work| Product/engineering |

A SEV-3 bug in a critical client's workflow might be P1 priority. A SEV-1 outage on a deprecated service might be P2 priority. Severity describes impact; priority drives scheduling.
