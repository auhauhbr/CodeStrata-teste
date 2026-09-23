# Security policy

CodeStrata reads source files and Git objects from repositories supplied by the user. It does not execute code from analyzed repositories.

Remote repositories are cloned into a temporary directory and removed after analysis. Source signatures are treated as text only.

If you discover a vulnerability that could cause command execution, path traversal, unsafe temporary-file behavior, or unintended credential exposure, please avoid posting exploit details in a public issue until a fix can be coordinated with the maintainer.
