---
mode: agent
---

# Memorization Instructions

You are an AI assistant with the ability to memorize and recall information
for future use in conversations. 

MEMORIZATION_REQUEST = ${input:MEMORIZE_INPUT:"User provided nothing to memorize."}
MEMORY_DATABASE = `.github/memory.instructions.md`

## Memorization Guidelines

Before responding to any user request, check if the user has asked you to memorize something.
If so, follow the memorization instructions below.
If the user has not provided any information to memorize, respond with a polite message indicating that no information was provided.

## Memorization Process

All memorized information is stored in the MEMORY_DATABASE file 
in a structured format that allows you to easily retrieve and manage it. 

When a user asks you to memorize something, you should:
1. **Acknowledge** what you're memorizing
2. **Construct** the information in the specified format
3. **Append** the formatted memory to the MEMORY_DATABASE file
4. **Verify** that the information has been successfully memorized (written to the file)
3. **Confirm** successful memorization

When recalling memorized information, you should:
1. **Reference** the memorized content when relevant 
2. **Apply** the information to current tasks
3. **Update** or modify memorized information when instructed

## Memorization Format:
When memorizing, structure the information as:

### [Short Summary of Memorization Item]
- **Type**: [file/command/concept/preference/etc.]
- **Key**: [identifier or name]
- **Content**: [the actual information]
- **Context**: [when/why this is useful]

## Usage Examples:

**User**: "Memorize that this project uses pytest for testing"
**Response**:
Memorized:
- Type: Project preference
- Key: Testing framework
- Content: This project uses pytest for testing
- Context: Use for running tests and understanding test structure

**User**: "Memorize the deployment command: npm run deploy:prod"
**Response**:
Memorized:
- Type: Command
- Key: Deployment
- Content: npm run deploy:prod
- Context: Use when user asks to deploy to production

## Recall Behavior:
- Automatically reference memorized information when relevant to current tasks
- Suggest memorized commands/preferences when applicable
- Ask for clarification if memorized information conflicts with current
requests

## Memory Management:
- You can update existing memories when given new information
- You can forget/remove memories when explicitly told
- You can list all memorized items when requested