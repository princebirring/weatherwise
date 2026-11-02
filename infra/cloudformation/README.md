# WeatherWise CloudFormation

See [the architecture overview](../ARCHITECTURE.md) for the application, AWS, and delivery flow.

`weatherwise-service.yaml` creates the production network, ALB, ECS Fargate service, private Bedrock AgentCore Runtime, CloudWatch/X-Ray observability, log groups, runtime IAM roles, and optional WAF. It does **not** create a database or persistent storage because the current app stores neither.

## Before deployment

1. Deploy `github-oidc-ecr-publisher.yaml` once. It creates the ECR repository, GitHub OIDC provider, and roles limited to publishing and deploying from this repository's `main` branch.
2. Set its outputs as GitHub Actions repository variables: `AWS_ECR_PUBLISH_ROLE_ARN`, `AWS_CLOUDFORMATION_DEPLOY_ROLE_ARN`, and `AWS_CLOUDFORMATION_EXECUTION_ROLE_ARN`. Also set `AWS_REGION=us-east-2`.
3. Create any paid-provider key in Secrets Manager. Put only the secret value in it; never put AWS credentials in a secret. The ECS task role supplies short-lived AWS credentials automatically.
4. Merge a checked change into `main`; GitHub Actions builds immutable ARM64 API and AgentCore images, publishes them, and deploys or updates the `weatherwise-prod` stack automatically.

The workflow supplies `ImageUri` automatically. For a manual deployment, use:

```bash
aws cloudformation deploy \
  --stack-name weatherwise-prod \
  --template-file infra/cloudformation/weatherwise-service.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ImageUri=ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/weatherwise:COMMIT_SHA \
    AgentRuntimeImageUri=ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/weatherwise:agentcore-COMMIT_SHA \
    ClimateAgentModelId=us.amazon.nova-micro-v1:0 \
    EnableWaf=true
```

Until a domain is added, omit `DomainName` and `HostedZoneId`; the output is an HTTP ALB URL. The ALB must use two subnets. Tasks receive public IPs for outbound weather-data calls, but their security group accepts port 8080 only from the ALB; the service cannot be reached directly. This avoids NAT Gateway charges for the hackathon.

## Custom domain and HTTPS

`weatherwise-domain.yaml` creates a Route 53 public hosted zone only. Deploy it once for `weatherwise.online`, then replace the GoDaddy nameservers with its `NameServers` output. Domain registration stays at GoDaddy. Do not delete the hosted zone after delegation.

Once GoDaddy shows the Route 53 nameservers, set these GitHub repository variables:

```text
WEATHERWISE_DOMAIN_NAME=weatherwise.online
ROUTE53_HOSTED_ZONE_ID=<HostedZoneId output>
```

The next merge to `main` automatically updates `weatherwise-prod`: it creates a DNS-validated ACM certificate in `us-east-2`, creates Route 53 Alias records for `weatherwise.online` and `www.weatherwise.online`, serves HTTPS, redirects HTTP to HTTPS, and redirects `www` to the apex domain. Keep the ACM validation records; ACM needs them to renew the certificate automatically.

## GitHub publishing role

Deploy `github-oidc-ecr-publisher.yaml` once with `CAPABILITY_NAMED_IAM`. It creates the ECR repository, GitHub OIDC provider, a minimal image-publishing role, and a CloudFormation deployer/execution-role pair restricted to workflows from `princebirring/weatherwise` on `main`. The default `GitHubOidcSubject` is the repository's immutable GitHub OIDC subject, which is more resistant to repository-name changes. The execution role has the permissions needed to create this stack's AWS resources, so protect `main` with review and required checks. If a prior failed deployment retained an ECR repository, supply its name in `ExistingEcrRepositoryName` to reuse it. If the AWS account already has the GitHub OIDC provider, do not deploy this template unchanged; reuse the existing provider in a small adjusted template instead.

Set these GitHub Actions repository variables after it finishes:

```text
AWS_REGION=us-east-2
AWS_ECR_PUBLISH_ROLE_ARN=<EcrPublisherRoleArn output>
AWS_CLOUDFORMATION_DEPLOY_ROLE_ARN=<CloudFormationDeployerRoleArn output>
AWS_CLOUDFORMATION_EXECUTION_ROLE_ARN=<CloudFormationExecutionRoleArn output>
```

The workflow uses OIDC, so it has no AWS access-key secret. It publishes immutable commit-SHA API and AgentCore images after the lint, test, website, image-build, and smoke-test jobs pass. It then deploys those immutable images through CloudFormation.

## AgentCore chat runtime

The public ALB never exposes AgentCore. The ECS task receives the runtime ARN as `WEATHERWISE_AGENT_RUNTIME_ARN` and may invoke only that ARN; AgentCore runs the Strands team and calls Bedrock using its own execution role. Each web-chat session gets a private AgentCore microVM session with a two-minute idle timeout. AgentCore Memory and Gateway are deliberately not created: there is no authenticated user identity to retain, and the local MCP facts server is packaged with the runtime.

The deployment creates CloudWatch/X-Ray permissions for AgentCore observability. To investigate a failed chat, inspect the runtime log group prefixed `/aws/bedrock-agentcore/runtimes/`, then its AgentCore trace, before changing prompts or model settings.

The stack also enables the account-wide CloudWatch Transaction Search destination and indexes 1% of spans. This lets the AgentCore console display sessions, traces, and spans after a short ingestion delay. Transaction Search sends spans to the managed `aws/spans` CloudWatch Logs group, so it adds CloudWatch log-ingestion and storage charges; keep the default low retention and use the 1% index unless higher sampling is needed.
