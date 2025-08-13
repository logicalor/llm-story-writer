# Chapter Event Extractor

Extract events from provided chapter content. Follow these instructions exactly.

<PREVIOUS_CHAPTER_RECAP>
{previous_chapter_recap}
</PREVIOUS_CHAPTER_RECAP>

<CHAPTER_CONTENT>
{chapter_content}
</CHAPTER_CONTENT>

## MANDATORY PROCESS

1. **Find each scene** in the chapter outline
2. **Write one to two sentences** describing what happens in that scene  
3. **Assign a type** (routine, departure, tragedy, medical, emotional)
4. **Create JSON entry** for that scene
5. **Repeat for ALL scenes**

## ABSOLUTE RULES

- **NO THINKING OR ANALYSIS** 
- **NO DEBATING WHAT TO INCLUDE**
- **DESCRIBE WHAT HAPPENS, NOTHING MORE**

## Example

**Chapter with 4 scenes:**
- Scene 1: Family has breakfast
- Scene 2: Car accident occurs  
- Scene 3: Paramedics arrive
- Scene 4: Amy goes to hospital

**Output:**
```json
[
  {
    "summary": "Family has breakfast together",
    "type": "routine"
  },
  {
    "summary": "Car accident occurs killing parents",
    "type": "tragedy"
  },
  {
    "summary": "Paramedics arrive and treat victims",
    "type": "medical"
  },
  {
    "summary": "Amy is taken to hospital",
    "type": "medical"
  }
]
```

## CRITICAL INSTRUCTIONS

**DO NOT:**
- Think about what's important
- Analyze plot significance  
- Debate what to include
- Write explanations
- Ask "what if" questions
- Consider alternatives

**ONLY:**
- Find scenes
- Describe what happens
- Output JSON

**OUTPUT ONLY THE JSON ARRAY. NO OTHER TEXT.**
