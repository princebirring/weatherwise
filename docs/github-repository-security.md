# GitHub repository protection

These settings must be applied in GitHub because repository access controls cannot be enforced by files committed to the repository.

## Branch ruleset

In **Settings → Rules → Rulesets**, create an active branch ruleset named `trusted-branches` targeting `*`.

- Enable **Restrict creations**, **Restrict updates**, and **Restrict deletions**.
- Add only you and the named collaborator to the bypass list. Do not grant a broad `Write` role bypass.
- Enable **Block force pushes**.

This prevents other users from creating or updating branches in the canonical repository. A public repository still allows anyone to create branches in their own fork; that cannot and should not be blocked.

Create a second ruleset targeting `main`:

- Require a pull request before merging.
- Require the `Server (lint + offline tests)`, `Website (lint + tests in en / hi / mr + build)`, and `Container image (build + smoke test)` checks.
- Require one approval from a code owner when practical.
- Block force pushes and deletions.

The ECR publishing workflow only receives AWS access through OIDC on a successful push to `main`. It cannot publish from a feature branch or pull request. GitHub recommends constraining AWS role trust to the repository and branch through the OIDC `sub` claim.
