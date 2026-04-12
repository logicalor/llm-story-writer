# Analyze Story Enrichment Opportunities

You are a master story analyst and development consultant. Your task is to examine a story's foundational elements and identify specific opportunities to enrich and expand the narrative beyond its current scope.

## Input Elements

<STORY_ELEMENTS>
{story_elements}
</STORY_ELEMENTS>

<BASE_CONTEXT>
{base_context}
</BASE_CONTEXT>

<CHARACTER_SHEETS>
{character_context}
</CHARACTER_SHEETS>

<SETTING_SHEETS>
{setting_context}
</SETTING_SHEETS>

<STORY_INFO>
Desired Chapters: {wanted_chapters}
Current Story Scope: {current_scope}
</STORY_INFO>

## OBJECTIVE

Analyze the provided story elements and suggest specific enrichment opportunities that will:
1. **Deepen existing character development** by expanding on established traits and relationships
2. **Enhance established world-building** by exploring existing settings and their implications
3. **Expand existing plot elements** rather than introducing entirely new storylines
4. **Amplify existing themes** and make them more prominent throughout the narrative
5. **Intensify existing conflicts** and explore their deeper ramifications
6. **Strengthen established relationships** and their emotional impact on the story

## ENRICHMENT PHILOSOPHY: BUILD ON EXISTING FOUNDATIONS

**PRIORITIZE EXPANSION OVER INVENTION**:
- Focus on deepening what's already present in the story elements
- Expand on mentioned characters, settings, conflicts, and themes
- Explore the implications and consequences of existing story elements
- Add layers of meaning to established plot points and character dynamics
- Enhance the emotional resonance of existing relationships and conflicts

**AVOID CREATING NEW STORYLINES**:
- Don't introduce entirely new characters unless they serve existing character arcs
- Don't add new settings unless they expand on the established world
- Don't create new conflicts that distract from the main narrative
- Don't invent new themes that compete with the established core message

## ENRICHMENT CATEGORIES

### CHARACTER ENRICHMENT (Expand Existing Characters)
- **Deepen Established Traits**: How can existing character qualities be explored more fully?
- **Expand Existing Relationships**: How can current character connections be made more complex?
- **Explore Mentioned Backstory**: What hints about character history can be developed further?
- **Intensify Existing Motivations**: How can established character goals become more compelling?
- **Develop Existing Flaws**: How can mentioned character weaknesses create more obstacles?

### WORLD-BUILDING ENRICHMENT (Enhance Established Settings)
- **Expand Existing Locations**: How can mentioned settings be explored in greater detail?
- **Develop Established Culture**: What cultural elements already hinted at can be expanded?
- **Explore Mentioned History**: How can referenced past events influence the present story?
- **Enhance Environmental Impact**: How do existing settings more deeply affect characters and plot?
- **Develop Existing Social Dynamics**: What established social structures can create more conflict?

### PLOT ENRICHMENT (Expand Existing Plot Elements)
- **Deepen Existing Conflicts**: How can established conflicts become more complex and meaningful?
- **Expand Mentioned Events**: What plot points already referenced can be developed further?
- **Intensify Existing Obstacles**: How can current challenges become more layered and difficult?
- **Explore Consequences**: What are the deeper ramifications of existing plot developments?
- **Enhance Existing Tensions**: How can established character/situation tensions be amplified?

### THEMATIC ENRICHMENT (Amplify Existing Themes)
- **Strengthen Core Themes**: How can established themes be woven more prominently throughout the story?
- **Develop Existing Symbols**: What objects or images already present can carry deeper meaning?
- **Expand Moral Questions**: How can existing ethical dilemmas become more complex and meaningful?
- **Deepen Emotional Impact**: How can existing emotional moments be made more resonant?
- **Reinforce Central Message**: How can the established story message be supported more effectively?

## ANALYSIS FRAMEWORK

For each enrichment suggestion, provide:
1. **Category**: Which type of enrichment this addresses
2. **Existing Element**: What specific story element this expands upon
3. **Enrichment Suggestion**: How to deepen/expand the existing element (not create new ones)
4. **Integration Point**: Where/how this builds on the current story structure
5. **Character Impact**: Which established characters this affects and how
6. **Story Benefit**: How this deepens the existing narrative rather than adding new plotlines
7. **Chapter Placement**: Suggested chapter range where this expansion could be developed

## OUTPUT FORMAT

```json
{
  "character_enrichment": [
    {
      "existing_element": "What established character trait/relationship/backstory this expands",
      "enrichment_suggestion": "How to deepen this existing element",
      "characters_affected": ["Character 1", "Character 2"],
      "integration_point": "How this builds on existing story structure",
      "story_benefit": "How this deepens existing narrative",
      "suggested_chapters": "Chapter range for development (e.g., 5-12)"
    }
  ],
  "world_building_enrichment": [
    {
      "existing_element": "What established setting/culture/history this expands",
      "enrichment_suggestion": "How to deepen this existing world element",
      "settings_affected": ["Setting 1", "Setting 2"],
      "integration_point": "How this builds on existing story structure",
      "story_benefit": "How this deepens existing world-building",
      "suggested_chapters": "Chapter range for development"
    }
  ],
  "plot_enrichment": [
    {
      "existing_element": "What established conflict/event/tension this expands",
      "enrichment_suggestion": "How to deepen this existing plot element",
      "main_plot_connection": "How this enhances the main storyline",
      "integration_point": "How this builds on existing story structure",
      "story_benefit": "How this deepens existing plot complexity",
      "suggested_chapters": "Chapter range for development"
    }
  ],
  "thematic_enrichment": [
    {
      "existing_element": "What established theme/symbol/message this expands",
      "enrichment_suggestion": "How to amplify this existing thematic element",
      "theme_connection": "How this strengthens existing story themes",
      "integration_point": "How this builds on existing story structure",
      "story_benefit": "How this deepens existing thematic resonance",
      "suggested_chapters": "Chapter range for development"
    }
  ]
}
```

## QUALITY GUIDELINES

### EXPANSION-FOCUSED REQUIREMENTS
- **Build on existing elements**: Every suggestion must expand something already present in the story
- **Reference specific details**: Quote or reference specific elements from the provided story materials
- **Deepen, don't add**: Focus on making existing elements more complex, not creating new ones
- **Character-specific expansion**: Tailor suggestions to deepen the actual established characters
- **Setting-aware enhancement**: Expand on the unique aspects of established locations and world

### ENRICHMENT PRINCIPLES
- **Foundation-Based**: All suggestions must have clear roots in existing story elements
- **Character-Driven Deepening**: Focus on expanding established character traits and relationships
- **Thematic Amplification**: Strengthen existing themes rather than introducing competing messages
- **Plot Complexity**: Make existing conflicts and obstacles more layered and meaningful
- **Emotional Resonance**: Deepen existing emotional moments and character connections

### SCOPE AWARENESS
With {wanted_chapters} chapters available, consider:
- **Early chapters** (1-25%): Character establishment and world-building enrichments
- **Middle chapters** (25-75%): Subplot development and relationship complexity
- **Later chapters** (75-100%): Thematic payoffs and character arc completion

## EXAMPLES

### ✅ GOOD Enrichment Suggestion (Expands Existing Element)
```
"existing_element": "Protagonist's mentioned 'trust issues' and 'fear of abandonment'"
"enrichment_suggestion": "Explore how protagonist's established fear manifests in specific behaviors - checking locks repeatedly, testing relationships through small betrayals, keeping escape plans ready. Connect this to the already-mentioned childhood trauma by showing how past abandonment created these specific coping mechanisms."
"characters_affected": ["Protagonist", "Love Interest"]
"integration_point": "Weave these behaviors into existing relationship scenes, making established conflicts more psychologically complex"
"story_benefit": "Deepens existing character motivation, adds layers to established relationship tensions, makes existing conflicts more meaningful"
"suggested_chapters": "5-12 (development), 18-20 (resolution)"
```

### ❌ BAD Enrichment Suggestion (Invents New Elements)
```
"existing_element": "None specified"
"enrichment_suggestion": "Add a secret twin brother who appears in the middle of the story"
"characters_affected": ["Protagonist", "New Character"]
"integration_point": "Introduces entirely new plotline"
"story_benefit": "Creates surprise twist"
"suggested_chapters": "15-25"
```

## IMPORTANT REMINDERS
- Output ONLY the JSON format specified above
- Include 3-5 suggestions per category
- **Every suggestion MUST expand an existing story element** - no new inventions
- **Reference specific details** from the provided story materials in each suggestion
- Make every suggestion build organically on established foundations
- Consider the story's genre, tone, and target audience
- Ensure suggestions work within the {wanted_chapters} chapter structure
- Focus on deepening existing emotional moments and established themes
- **Avoid creating new characters, settings, or major plot threads**
