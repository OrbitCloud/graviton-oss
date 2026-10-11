# Task 02: Use config.name in Pulumi ComponentResource name

> Status: done

## Goal
Change the Pulumi `ComponentResource` name in `StorageAccount.__init__` from `f"st-{self.stack.workload_name}"` to `f"st-{self.config.name}"` so multiple storage accounts get unique resource names.

## Acceptance Criteria
- [ ] ComponentResource name incorporates `config.name`
- [ ] Two storage accounts with different names produce different Pulumi resource names
- [ ] Tests verify unique naming
