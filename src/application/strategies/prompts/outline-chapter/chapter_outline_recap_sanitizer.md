I have the following full story recap:
<RECAP>
{previous_chapter_recap}
</RECAP>
(if there is nothing here, then we're at the latest point in the story)

and I need to combine it with a recap from the latest story developments:
<LATEST_RECAP>
{recap}
</LATEST_RECAP>

The full story is provided in chronological order. The story itself starts on {story_start_date}.

Combine the latest recap with the full recap and output it according to the following template

<TEMPLATE>
## Recap

### Deep History
(any events over 1 year prior to the latest event)
**Date and time started - date and time ended **:  A sentence describing the event

### A Year to 6 Months Ago
(any events more than 6 months prior and up to 1 year prior to the latest event)
**Date and time started - date and time ended **:  A sentence describing the event

### A While Ago
(any events more than 3 months prior and up to 6 months prior to the latest event)
**Date and time started - date and time ended **:  A sentence describing the event

### Recently
(any events more than 1 week prior and up to 3 months prior to the latest event)
**Date and time started - date and time ended **: A sentence describing the event

### Current
(the latest event, and any events up to 1 week prior to the latest event)
#### Date and time started - date and time ended
  - **Key Event(s)**: List of events, one line, sentence(s)
  - **Location(s)**: List of locations, one line
  - **Character development**: List of character developments, one line, sentence(s)
  - **Recurring symbolism or motifs used**: List of recurring elements, and possible escalation related to them, one line, sentence(s)
</TEMPLATE>

If there are no events for a particular section, retain the section's title but leave its content blank.

IMPORTANT: Just output the formatted response. No TEMPLATE / other XML / HTML tags , commentary, metadata or code wrapper.