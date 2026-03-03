# Review 02

> Status: pending-dev
> Date: 2026-03-03
> Reviewer: Code Review Agent
> Verdict: REQUEST CHANGES

## Previous Review Status

- [x] Issue from review-01, Critical #2: `initial_domain_prefix` had full domain instead of prefix only - FIXED. Value changed to `gravitonusersdev` with clarifying comment at `/Users/on/src/graviton-oss/.claude/worktrees/stack-examples/development/14-entra-external-id/Pulumi.dev.yaml:17`.
- [x] Issue from review-01, Important #2: Three app workload projects shared the same Pulumi project name - FIXED. Each now has a unique name (`app_workload_http`, `app_workload_job_scheduled`, `app_workload_job_event`) in their respective `Pulumi.yaml` files.
- [x] Issue from review-01, Important #4: Self-referencing `stack://` in networking private DNS zones - FIXED. The `linked_vnets` self-reference was removed and a clarifying comment was added at `/Users/on/src/graviton-oss/.claude/worktrees/stack-examples/development/04-networking/Pulumi.dev.yaml:50-52`.
- [ ] Issue from review-01, Important #5: KEDA `accountName` may not match deployed storage account name - PARTIALLY FIXED, NEW BUG INTRODUCED (see below).

## New Findings

### Critical (Must Fix)

1. **[`/Users/on/src/graviton-oss/.claude/worktrees/stack-examples/development/09-app-workload-job-event/Pulumi.dev.yaml:24`]** The KEDA `accountName` value `steventdevne01` is incorrect. Tracing through the CDK naming logic:

   - `StorageAccount.__init__` (line 120-122 of `components/orbitcloud_graviton/az_storage/storage_account.py`) calls `self.stack.name_for(resource_type=storage.StorageAccount, workload_name=self.config.name)` with `config.name = "event"`
   - `name_for` calls `resource_namer` with `workload_name="event"`, `env="dev"`, `location="northeurope"` (from ESC/azure-native config)
   - Storage account metadata has `prefix: st`, `alphanumeric: true`, `lowercase: true`
   - `location_abbr("northeurope")` returns `"neu"` (3 characters), confirmed by test assertions in `test/components/orbitcloud_graviton/az_lib/test_resource_naming.py:11` and the naming snapshot at `test/components/orbitcloud_graviton/az_lib/test_metadata_snapshot.py:897` which shows `stworkloadtestneu01`
   - With `alphanumeric=true`, each element is `.title()`d and joined with empty separator: `St` + `Event` + `Dev` + `Neu` + `01` = `StEventDevNeu01`
   - With `lowercase=true`, the final result is `steventdevneu01`

   The config currently says `steventdevne01` (missing the `u` in `neu`). The comment on line 23 also references this wrong value.

   **Fix:** Change `accountName` from `steventdevne01` to `steventdevneu01`, and update the comment on line 23 accordingly.

### Important (Should Fix)

No new important issues.

### Suggestions (Consider)

No new suggestions.

### Praise

- The developer's approach to the fixes was thorough. The removal of the `linked_vnets` self-reference with an explanatory comment about hub VNet auto-linking is exactly the right level of documentation.
- The `initial_domain_prefix` fix correctly identified the Azure CIAM API expectation and added a concise, helpful comment.
- The unique project names now accurately reflect each workload variant, which prevents Pulumi backend conflicts and improves discoverability.

## Summary

**Overall assessment: REQUEST CHANGES**

Three of the four issues from review-01 were correctly resolved. The fourth fix (KEDA `accountName` matching the CDK naming output) contains a typo: the location abbreviation for `northeurope` is `neu` (3 characters), not `ne` (2 characters). The config value `steventdevne01` should be `steventdevneu01`.

This is a single character fix in one file. Once corrected, the implementation is ready for approval.

**Estimated effort to address feedback:** Under 5 minutes. One value change and one comment update in `development/09-app-workload-job-event/Pulumi.dev.yaml`.
