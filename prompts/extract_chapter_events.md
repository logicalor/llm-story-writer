# Chapter Event Extractor

Extract events from provided chapter content. Follow these instructions exactly.

<PREVIOUS_CHAPTER_RECAP>
{previous_chapter_recap}
</PREVIOUS_CHAPTER_RECAP>

<CHAPTER_CONTENT>
{chapter_content}
</CHAPTER_CONTENT>

<WIKI_CONTEXT>
{wiki_context}
</WIKI_CONTEXT>

<RELATED_RECAP_HISTORY>
{related_recap_history}
</RELATED_RECAP_HISTORY>

## MANDATORY PROCESS

1. **Find each scene** in the chapter outline
2. **Write one to two sentences** describing what happens in that scene  
3. **Assign a type** (routine, departure, tragedy, medical, emotional)
4. **List participants** — character names present in the scene, using canonical names from the wiki context
5. **List locations** — location names where the scene occurs, using canonical names from the wiki context
6. **Create JSON entry** for that scene
7. **Repeat for ALL scenes**

## ABSOLUTE RULES

- **NO THINKING OR ANALYSIS** 
- **NO DEBATING WHAT TO INCLUDE**
- **DESCRIBE WHAT HAPPENS, NOTHING MORE**
- **participants** must be an array of strings (character names). Use `[]` if no named characters appear.
- **locations** must be an array of strings (location names). Use `[]` if no named location is established.

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
    "type": "routine",
    "participants": ["Amy Miller", "Thomas Miller", "Sarah Miller"],
    "locations": ["Miller Family Home"]
  },
  {
    "summary": "Car accident occurs killing parents",
    "type": "tragedy",
    "participants": ["Thomas Miller", "Sarah Miller"],
    "locations": ["City Road"]
  },
  {
    "summary": "Paramedics arrive and treat victims",
    "type": "medical",
    "participants": ["Thomas Miller", "Sarah Miller"],
    "locations": ["City Road"]
  },
  {
    "summary": "Amy is taken to hospital",
    "type": "medical",
    "participants": ["Amy Miller"],
    "locations": ["City Hospital"]
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

## Input

1. **Previous Chapter Recap**
2. **Chapter Content**
3. **Wiki Context** (canonical character names/slugs for tagging participants)
4. **Related Recap History** (recent chapter aggregates for consistency context)

## Processing Note

Use {wiki_context} for canonical character names when tagging participants. Use {related_recap_history} to avoid duplicating events already captured in prior chapter recaps.

**OUTPUT ONLY THE JSON ARRAY. NO OTHER TEXT.**
