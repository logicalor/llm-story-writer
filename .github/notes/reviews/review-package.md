== REVIEW PACKAGE ==

=== BRANCH ===
fix/issue-263-stale-opencode-tools-refs

=== COMMIT LOG ===
701b036 docs(agents): sweep stale .opencode/tools/ references from agent bodies (#263)
53ccedb docs(agents): additional stale-reference cleanup (#263)

=== CHANGED FILES ===
.opencode/agents/coder.md
.opencode/agents/documenter.md
.opencode/agents/orchestrator-v3.md
.opencode/agents/planner.md

This is a documentation-only PR that sweeps stale references to the deleted `.opencode/tools/` directory from four Opencode agent files. The `.opencode/tools/` directory was deleted per ADR 007 (Python-native migration). All references now point to `src/tools/` (the current Python-native tool directory).

Key substitution patterns:
- "TypeScript OpenCode tool wrappers" → removed or replaced with "Python tools"
- `.opencode/tools/` → `src/tools/`
- Tool verification rules reframed from TypeScript/Zod to Python `argparse`
- Documenter edit permissions expanded to include `.opencode/agents/**`

=== KEY DIFF SUMMARY ===

coder.md:
- description frontmatter: removed "TypeScript OpenCode tool wrappers"
- Rule 7 deletion-cleanup: reframed for Python scripts, updated grep sweep paths
- Security heading: "TypeScript tool wrappers:" → "Subprocess invocation:"
- Tool verification rule (line 90): removed all TS/Zod references, now references Python source only
- Implementation Order step 3: "OpenCode tool definitions in `.opencode/tools/`" → "This step is retired per ADR 007; all tools are Python-native in `src/tools/`."
- CLI modification paragraph: removed TS wrapper/Zod references
- Removed entire "TypeScript `data` parameter type" paragraph

orchestrator-v3.md:
- Researcher dispatch prompt: "TypeScript OpenCode tool wrappers in `.opencode/tools/`" → "Python tools in `src/tools/`"
- Plan template "Affected Areas": removed "TypeScript tool wrappers" option
- Plan template "Implementation" checklist: removed "TypeScript wrappers"

planner.md:
- OpenCode Tools section: "TypeScript wrappers: existing tool definitions in `.opencode/tools/`" → "Python tools: existing tool scripts in `src/tools/`"
- Task template key file: `.opencode/tools/tool-name.ts` → `src/tools/tool_name.py`
- Task ordering rule 2: "Python domain logic before TypeScript wrappers" → "Python domain logic before tool CLI scripts"

documenter.md:
- edit permissions: added `.opencode/agents/**`: "allow"
- docs/tools.md table cell: "TypeScript wrappers and Python scripts" → "Python scripts"
- inventory table instruction: `ls .opencode/tools/` removed
- Feature doc template: removed `.opencode/tools/tool-name.ts` list item

== END REVIEW PACKAGE ==
