---
applyTo: "**"
---

# Database of Memorized Information

The following content is all of the memorized information that the AI assistant has stored. This database is structured to allow easy retrieval and management of information.

## Memorized Information

### Project Root Command Execution Tool
- **Type**: Command utility
- **Key**: razr function
- **Content**: Source the `.lz` file in project root to get access to `razr` function that runs any command from the project root directory as working directory
- **Context**: Use when needing to run commands from project root regardless of current directory (e.g., `razr git commit` runs git commit from project root even if in subdirectory like notes/)

### Python Virtual Environment Setup
- **Type**: Project configuration
- **Key**: Python executable path
- **Content**: `/home/matt/Repospace/com/github/matt-wiley/agentics/.venv/bin/python`
- **Context**: Use this specific Python executable when running Python commands, scripts, or tests in this project. The project has a virtual environment set up with uv.

### Documentation Organization Standard
- **Type**: Project preference
- **Key**: Documentation file location
- **Content**: Create new documentation files in either the `notes/` directory or the `docs/` directory, or an appropriate sub-directory of those
- **Context**: This includes workplans, task summaries, and other markdown or plaintext files that provide additional context about the project. Use for any documentation creation tasks.

