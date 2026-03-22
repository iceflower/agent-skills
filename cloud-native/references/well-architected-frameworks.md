# Well-Architected Frameworks: Cross-Cloud Reference

This document summarizes the core pillars of the AWS, GCP, and Azure Well-Architected frameworks and provides actionable guidance for each.

---

## Framework Overview

All three major cloud providers define a Well-Architected framework to help organizations build secure, high-performing, resilient, and efficient infrastructure. While terminology differs, the core principles are consistent.

| Pillar                 | AWS Well-Architected | GCP Architecture Framework | Azure Well-Architected |
| ---------------------- | -------------------- | -------------------------- | ---------------------- |
| Operational Excellence | Yes                  | Yes (Operational)          | Yes                    |
| Security               | Yes                  | Yes                        | Yes                    |
| Reliability            | Yes                  | Yes                        | Yes                    |
| Performance Efficiency | Yes                  | Yes (Performance)          | Yes                    |
| Cost Optimization      | Yes                  | Yes (Cost)                 | Yes                    |
| Sustainability         | Yes                  | Yes                        | Yes                    |

---

## Pillar 1: Operational Excellence

### Operational Excellence Principle

Continuously improve processes and procedures to deliver business value, including monitoring, automation, and evolving operational practices.

### Operational Excellence Practices

| Practice               | AWS                              | GCP                             | Azure                          |
| ---------------------- | -------------------------------- | ------------------------------- | ------------------------------ |
| Infrastructure as Code | CloudFormation, CDK, Terraform   | Deployment Manager, Terraform   | ARM/Bicep, Terraform           |
| Automated Deployments  | CodePipeline, CodeDeploy         | Cloud Build, Cloud Deploy       | Azure DevOps, GitHub Actions   |
| Runbooks               | Systems Manager Automation       | Cloud Workflows                 | Azure Automation               |
| Change Management      | Change Manager, CloudTrail       | Cloud Audit Logs                | Activity Log, Change Analysis  |
| Observability          | CloudWatch, X-Ray                | Cloud Monitoring, Cloud Trace   | Azure Monitor, App Insights    |

### Operational Excellence Rules

- Automate operational procedures -- manual runbooks should be exception, not norm
- Define operational metrics and alerts for every workload
- Perform post-incident reviews and feed learnings back into operations
- Use feature flags to separate deployment from release
- Maintain infrastructure code with the same rigor as application code (code review, testing, CI/CD)

---

## Pillar 2: Security

### Security Principle

Protect information, systems, and assets through risk assessments, defense in depth, and security best practices.

### Security Practices

| Practice   | AWS                   | GCP                     | Azure                  |
| ---------- | --------------------- | ----------------------- | ---------------------- |
| Identity   | IAM, SSO              | Cloud IAM, Workload ID  | Entra ID, RBAC         |
| Network    | VPC, Security Groups  | Cloud Armor, Firewall   | VNet, NSG, Firewall    |
| Data       | KMS, Macie            | Cloud KMS, DLP          | Key Vault, Purview     |
| Threats    | GuardDuty, Sec Hub    | Security Command Center | Defender, Sentinel     |
| Secrets    | Secrets Manager, SSM  | Secret Manager          | Key Vault              |

### Security Rules

- Apply least privilege to all IAM policies and service accounts
- Encrypt all data at rest and in transit
- Automate security compliance checks in CI/CD pipelines
- Enable logging and auditing for all access and changes
- Use managed secret stores -- never store secrets in code, config files, or environment variable files committed to VCS
- Rotate credentials automatically on a defined schedule
- Segment networks: public, private, and isolated tiers

### Zero Trust Principles

| Principle              | Description                                                       |
| ---------------------- | ----------------------------------------------------------------- |
| Verify Explicitly      | Authenticate and authorize every request based on all data points |
| Least Privilege Access | Grant minimum permissions needed, just-in-time access             |
| Assume Breach          | Design as if attackers are already inside the network             |

---

## Pillar 3: Reliability

### Reliability Principle

Ensure workloads perform their intended function correctly and consistently, recover from failures, and meet demand.

### Reliability Practices

| Practice   | AWS                 | GCP                 | Azure                  |
| ---------- | ------------------- | ------------------- | ---------------------- |
| Multi-AZ   | Multi-AZ, Route 53  | Regional, Cloud DNS | Availability Zones     |
| Auto Scale | ASG, ECS            | MIG, GKE            | VMSS, AKS              |
| Backup     | AWS Backup, S3      | Snapshots, GCS      | Azure Backup, Blob     |
| Health     | ELB health checks   | LB health checks    | Azure LB health probes |
| Chaos      | Fault Injection Sim | Chaos Monkey        | Azure Chaos Studio     |

### Reliability Rules

- Define Recovery Time Objective (RTO) and Recovery Point Objective (RPO) for every workload
- Test failure recovery procedures regularly, not just when incidents occur
- Deploy across multiple availability zones as the minimum redundancy level
- Implement circuit breakers and retries with exponential backoff for all external calls
- Design for graceful degradation -- partial functionality is better than total failure
- Automate failover and recovery; manual intervention should be a last resort

### Reliability Targets

| Availability | Downtime/Year | Downtime/Month | Typical Use Case          |
| ------------ | ------------- | -------------- | ------------------------- |
| 99%          | 3.65 days     | 7.3 hours      | Internal tools            |
| 99.9%        | 8.76 hours    | 43.8 minutes   | Business applications     |
| 99.95%       | 4.38 hours    | 21.9 minutes   | Important public services |
| 99.99%       | 52.6 minutes  | 4.38 minutes   | Critical infrastructure   |
| 99.999%      | 5.26 minutes  | 26.3 seconds   | Financial, healthcare     |

---

## Pillar 4: Performance Efficiency

### Performance Efficiency Principle

Use computing resources efficiently to meet requirements, and maintain that efficiency as demand changes and technologies evolve.

### Performance Efficiency Practices

| Practice           | AWS                            | GCP                            | Azure                           |
| ------------------ | ------------------------------ | ------------------------------ | ------------------------------- |
| Right-Sizing       | Compute Optimizer, Advisor     | Recommender, Assist            | Advisor, Cost Management        |
| Caching            | ElastiCache, CloudFront        | Memorystore, Cloud CDN         | Azure Cache for Redis, CDN      |
| Serverless         | Lambda, Fargate, Aurora SL     | Cloud Functions, Run           | Azure Functions, Container Apps |
| Database Selection | DynamoDB, RDS, Aurora          | Spanner, Cloud SQL             | Cosmos DB, Azure SQL            |
| Load Testing       | Distributed Load Testing       | Third-party tools              | Azure Load Testing              |

### Performance Efficiency Rules

- Select the right compute type for the workload (VM, container, serverless, GPU)
- Use caching at every layer: CDN for static, application cache for computed, database cache for queries
- Measure and benchmark performance regularly, not just at launch
- Adopt managed services over self-managed when performance requirements match
- Set performance budgets and monitor against them continuously
- Use asynchronous processing for operations that do not require immediate response

### Compute Selection Guide

| Workload Type      | Recommended Compute                             |
| ------------------ | ----------------------------------------------- |
| Stateless HTTP     | Containers (Kubernetes, ECS, Cloud Run)         |
| Event-driven       | Serverless Functions (Lambda, Cloud Functions)  |
| Long-running batch | Spot/Preemptible VMs + Job scheduler            |
| GPU/ML workloads   | GPU instances, managed ML platforms             |
| Legacy monolith    | VMs with auto-scaling groups                    |
| Stream processing  | Containers with event-driven autoscaling (KEDA) |

---

## Pillar 5: Cost Optimization

### Cost Optimization Principle

Avoid unnecessary costs, understand spending, and select the most cost-effective resources.

### Cost Optimization Practices

| Practice          | AWS                     | GCP                    | Azure                    |
| ----------------- | ----------------------- | ---------------------- | ------------------------ |
| Visibility        | Cost Explorer, Budgets  | Billing Reports        | Cost Management, Budgets |
| Right-Sizing      | Compute Optimizer       | Recommender            | Advisor                  |
| Reserved Capacity | Reserved, Savings Plans | Committed Use          | Reserved, Savings Plans  |
| Spot/Preemptible  | Spot Instances          | Spot VMs (Preemptible) | Spot VMs                 |
| Resource Tagging  | Cost Allocation Tags    | Labels                 | Tags                     |

### Cost Optimization Rules

- Tag all resources for cost attribution (team, project, environment)
- Review and right-size resources monthly
- Use auto-scaling to match capacity to demand (do not over-provision)
- Use spot/preemptible instances for fault-tolerant, stateless workloads
- Shut down non-production environments outside business hours
- Set budget alerts at 50%, 80%, and 100% of expected spend
- Evaluate reserved capacity for steady-state workloads (break-even typically at 40-60% utilization)
- Regularly review and terminate unused resources (unattached volumes, idle load balancers, orphaned snapshots)

### Cost Optimization Hierarchy

```text
1. Eliminate waste (unused resources, over-provisioned instances)
2. Right-size (match resource size to actual usage)
3. Use pricing models (reserved, spot, committed use)
4. Architect for cost (serverless, event-driven, shared resources)
5. Negotiate (enterprise agreements, volume discounts)
```

---

## Pillar 6: Sustainability

### Sustainability Principle

Minimize the environmental impact of running cloud workloads through efficient use of resources and responsible practices.

### Sustainability Practices

| Practice            | AWS                        | GCP                         | Azure                      |
| ------------------- | -------------------------- | --------------------------- | -------------------------- |
| Carbon Reporting    | Customer Carbon Footprint  | Carbon Footprint dashboard  | Emissions Impact Dashboard |
| Efficient Compute   | Graviton (ARM) instances   | Tau VMs, Arm-based          | Arm-based VMs (Ampere)     |
| Region Selection    | Renewable energy regions   | Carbon-free energy regions  | Renewable energy regions   |
| Resource Efficiency | Auto-scaling, right-sizing | Active Assist, auto-scaling | Auto-scaling, Advisor      |

### Sustainability Rules

- Choose regions powered by renewable energy when latency requirements allow
- Use ARM-based instances for compatible workloads (typically more power-efficient)
- Optimize code and algorithms to reduce compute requirements
- Minimize data transfer by co-locating resources and using CDNs
- Set auto-scaling minimums to zero for non-critical workloads during off-peak hours
- Monitor and report carbon footprint as part of operational metrics

---

## Cross-Pillar Interactions

The six pillars are interdependent. Decisions in one pillar affect others.

| Decision                       | Performance | Cost    | Reliability | Security |
| ------------------------------ | ----------- | ------- | ----------- | -------- |
| Add caching layer              | Improves    | Adds    | Adds risk   | Neutral  |
| Deploy multi-region            | May vary    | Adds    | Improves    | Neutral  |
| Use serverless                 | Auto-scales | Reduces | Improves    | Shared   |
| Encrypt everything             | Minor cost  | Adds    | Neutral     | Improves |
| Right-size instances           | Match       | Reduces | Neutral     | Neutral  |
| Use spot/preemptible instances | Same        | Reduces | Adds risk   | Neutral  |

### Trade-Off Resolution Rules

- Security is non-negotiable -- never compromise security for cost or performance
- Reliability requirements drive architecture decisions; cost and performance adjust around them
- Cost optimization should never reduce availability below the defined SLA
- When pillars conflict, prioritize in order: Security > Reliability > Performance > Cost > Sustainability

---

## Quick Reference: Provider Service Mapping

### Compute Services

| Use Case              | AWS                 | GCP              | Azure            |
| --------------------- | ------------------- | ---------------- | ---------------- |
| VMs                   | EC2                 | Compute Engine   | Virtual Machines |
| Containers (Managed)  | ECS, EKS            | GKE              | AKS              |
| Serverless Containers | Fargate, App Runner | Cloud Run        | Container Apps   |
| Functions             | Lambda              | Cloud Functions  | Azure Functions  |

### Storage Services

| Use Case       | AWS | GCP             | Azure         |
| -------------- | --- | --------------- | ------------- |
| Object Storage | S3  | Cloud Storage   | Blob Storage  |
| Block Storage  | EBS | Persistent Disk | Managed Disks |
| File Storage   | EFS | Filestore       | Azure Files   |

### Database Services

| Use Case            | AWS                    | GCP                | Azure                   |
| ------------------- | ---------------------- | ------------------ | ----------------------- |
| Relational          | RDS, Aurora            | Cloud SQL, AlloyDB | Azure SQL, PostgreSQL   |
| NoSQL (Document)    | DynamoDB               | Firestore          | Cosmos DB               |
| NoSQL (Wide Column) | DynamoDB, Keyspaces    | Bigtable           | Cosmos DB (Cassandra)   |
| In-Memory Cache     | ElastiCache            | Memorystore        | Azure Cache for Redis   |
| Global Distributed  | DynamoDB Global Tables | Spanner            | Cosmos DB               |

### Networking Services

| Use Case      | AWS         | GCP                  | Azure                    |
| ------------- | ----------- | -------------------- | ------------------------ |
| CDN           | CloudFront  | Cloud CDN            | Azure CDN / Front Door   |
| DNS           | Route 53    | Cloud DNS            | Azure DNS                |
| Load Balancer | ALB/NLB/GLB | Cloud Load Balancing | Azure Load Balancer / AG |
| API Gateway   | API Gateway | Apigee, API Gateway  | API Management           |
| Service Mesh  | App Mesh    | Anthos Service Mesh  | Open Service Mesh        |
