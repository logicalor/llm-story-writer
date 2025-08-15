# Scene Content Cleanup

You are tasked with cleaning up LLM output which contains a story scene.

## Input
The raw scene content that may contain:
- Commentary about the writing process
- Two or more copies or variants of the scene
- Code wrapper ("```") markdown
- Markdown headings with hashes (##, ### etc)
- Meta-text about the story structure
- Instructions or notes to the writer
- Any other non-narrative content that isn't the scene title

## Task
Clean the content by:
1. Removing all commentary and meta-text
2. Removing double-ups of the scene content - if there are more than one, just keep the last one
3. Removing any instructions or notes
4. Removing any code wrapper markup
5. Removing any Markdown headings with hashes

## Output
Return only the cleaned scene title and content without any additional commentary or formatting instructions.

Here is the output you need clean:
<SCENE_OUTPUT>
{scene_content}
</SCENE_OUTPUT>

## Example of what to expect:
<EXAMPLE_INPUT>
Here's a scene that shows the tension between the characters. The dialogue should feel natural and the setting should be atmospheric. Let me write this scene:

**Scene One: The Discussion**

John walked into the dimly lit room, his footsteps echoing on the wooden floor. The air was thick with tension. He could feel Sarah's eyes on him from across the room.

"John," she said, her voice barely above a whisper. "We need to talk."

The tension in the room was palpable. John could feel Sarah's eyes on him from across the room. 

He took a deep breath and stepped forward.

---
### Summary

This scene establishes the conflict between John and Sarah. The dialogue should feel natural and the setting should be atmospheric.

### Final Output

```markdown
John walked into the dimly lit room, his footsteps echoing on the wooden floor. The air was thick with tension. He could feel Sarah's eyes on him from across the room.

"John," she said, her voice barely above a whisper. "We need to talk."

The tension in the room was palpable. John could feel Sarah's eyes on him from across the room. He took a deep breath and stepped forward.
```
{/boxed}
</EXAMPLE_INPUT>

This is an example of what should be extracted from the input
<EXAMPLE_OUTPUT>
**Scene One: The Discussion**

John walked into the dimly lit room, his footsteps echoing on the wooden floor. The air was thick with tension. He could feel Sarah's eyes on him from across the room.

"John," she said, her voice barely above a whisper. "We need to talk."

The tension in the room was palpable. John could feel Sarah's eyes on him from across the room. He took a deep breath and stepped forward.
</EXAMPLE_OUTPUT>
(without the EXAMPLE_OUTPUT tags)

Refer to the examples to understand how to extract the expected output.

Don't add any commentary of your own, and don't include the SCENE_OUTPUT tags.
