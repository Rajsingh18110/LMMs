# LMMs Security Policy

See the comprehensive [Security Documentation](docs/SECURITY.md) for details on:
- Execution Policy (`ExecPolicy`) as a first-layer filter vs kernel sandbox containment
- Known bypass classes for command filters (`python -c`, `eval`, `base64|sh`, `find -delete`, `xargs`)
- Bubblewrap and Landlock LSM isolation boundaries
- Worktree and checkpoint safety guarantees
