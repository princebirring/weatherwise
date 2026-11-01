# WeatherWise CloudFormation

`weatherwise-service.yaml` creates the production network, ALB, ECS Fargate service, log group, runtime IAM roles, and optional WAF. It does **not** create a database or persistent storage because the current app stores neither.

## Before deployment

1. Deploy `github-oidc-ecr-publisher.yaml` once. It creates the ECR repository, GitHub OIDC provider, and roles limited to publishing and deploying from this repository's `main` branch.
2. Set its outputs as GitHub Actions repository variables: `AWS_ECR_PUBLISH_ROLE_ARN`, `AWS_CLOUDFORMATION_DEPLOY_ROLE_ARN`, and `AWS_CLOUDFORMATION_EXECUTION_ROLE_ARN`. Also set `AWS_REGION=us-east-2`.
3. Create any paid-provider key in Secrets Manager. Put only the secret value in it; never put AWS credentials in a secret. The ECS task role supplies short-lived AWS credentials automatically.
4. Merge a checked change into `main`; GitHub Actions builds, publishes an immutable ARM64 image, and deploys or updates the `weatherwise-prod` stack automatically.

The workflow supplies `ImageUri` automatically. For a manual deployment, use:

```bash
aws cloudformation deploy \
  --stack-name weatherwise-prod \
  --template-file infra/cloudformation/weatherwise-service.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ImageUri=ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/weatherwise:COMMIT_SHA \
    ClimateAgentModelId=us.amazon.nova-micro-v1:0 \
    EnableWaf=true
```

Until a domain is added, omit `CertificateArn`; the output is an HTTP ALB URL. Supplying a regional ACM certificate ARN later adds an HTTPS listener and redirects HTTP to HTTPS. The ALB must use two subnets. Tasks receive public IPs for outbound weather-data calls, but their security group accepts port 8080 only from the ALB; the service cannot be reached directly. This avoids NAT Gateway charges for the hackathon.

## GitHub publishing role

Deploy `github-oidc-ecr-publisher.yaml` once with `CAPABILITY_NAMED_IAM`. It creates the ECR repository, GitHub OIDC provider, a minimal image-publishing role, and a CloudFormation deployer/execution-role pair restricted to workflows from `princebirring/weatherwise` on `main`. The execution role has the permissions needed to create this stack's AWS resources, so protect `main` with review and required checks. If a prior failed deployment retained an ECR repository, supply its name in `ExistingEcrRepositoryName` to reuse it. If the AWS account already has the GitHub OIDC provider, do not deploy this template unchanged; reuse the existing provider in a small adjusted template instead.

Set these GitHub Actions repository variables after it finishes:

```text
AWS_REGION=us-east-2
AWS_ECR_PUBLISH_ROLE_ARN=<EcrPublisherRoleArn output>
AWS_CLOUDFORMATION_DEPLOY_ROLE_ARN=<CloudFormationDeployerRoleArn output>
AWS_CLOUDFORMATION_EXECUTION_ROLE_ARN=<CloudFormationExecutionRoleArn output>
```

The workflow uses OIDC, so it has no AWS access-key secret. It publishes both an immutable commit-SHA tag and the moving `main` tag only after the lint, test, website, image-build, and smoke-test jobs pass. It then deploys the same immutable image through CloudFormation.
