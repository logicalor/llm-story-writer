import { readFileSync, readdirSync, statSync } from "fs";
import { join, resolve } from "path";

// --- YAML frontmatter parser (no dependencies) ---

/**
 * Minimal YAML frontmatter parser — no external dependencies.
 *
 * Known limitations:
 * - Single-line `key: value` pairs only
 * - One level of nesting (indented `key: value` under a parent)
 * - No YAML arrays or block scalars (`|`, `>`)
 * - Empty nested values (e.g., `  L1:` with no text after colon-space)
 *   are silently skipped
 */
function parseFrontmatter(content: string): {
  metadata: Record<string, any>;
  body: string;
} {
  if (!content.startsWith("---")) return { metadata: {}, body: content };
  const parts = content.split("---");
  if (parts.length < 3) return { metadata: {}, body: content };

  const metadata: Record<string, any> = {};
  const yamlLines = parts[1].trim().split("\n");
  let currentParent: string | null = null;

  for (const line of yamlLines) {
    // Indented sub-key (nested under parent)
    const nestedMatch = line.match(/^[ \t]+(\w[\w-]*)\s*:\s*(.+)$/);
    if (nestedMatch && currentParent) {
      if (typeof metadata[currentParent] !== "object") {
        metadata[currentParent] = {};
      }
      const value = nestedMatch[2].trim();
      metadata[currentParent][nestedMatch[1]] = unquote(value);
      continue;
    }

    // Top-level key
    const topMatch = line.match(/^(\w[\w-]*)\s*:\s*(.*)$/);
    if (topMatch) {
      const key = topMatch[1];
      const raw = topMatch[2].trim();
      if (raw === "" || raw === undefined) {
        // Parent key with no inline value — next indented lines are children
        currentParent = key;
        metadata[key] = {};
      } else {
        currentParent = null;
        metadata[key] = unquote(raw);
      }
    }
  }

  const body = parts.slice(2).join("---").trimStart();
  return { metadata, body };
}

function unquote(value: string): string {
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }
  return value;
}

// --- Token estimation ---

function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

// --- Safe file helpers ---

function safeReadFile(filePath: string): string | null {
  try {
    return readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}

function safeReadDir(dirPath: string): string[] {
  try {
    return readdirSync(dirPath);
  } catch {
    return [];
  }
}

function safeStat(filePath: string): { mtimeMs: number } | null {
  try {
    return statSync(filePath);
  } catch {
    return null;
  }
}

// --- Path validation ---

function isWithinBase(target: string, base: string): boolean {
  const resolved = resolve(target);
  const resolvedBase = resolve(base);
  return resolved.startsWith(resolvedBase + "/") || resolved === resolvedBase;
}

// --- Story detection ---

function detectStory(storiesDir: string): string | null {
  const entries = safeReadDir(storiesDir);
  if (entries.length === 0) return null;

  let bestName: string | null = null;
  let bestMtime = -1;

  for (const entry of entries) {
    const stateFile = join(storiesDir, entry, "state.json");
    if (!isWithinBase(stateFile, storiesDir)) continue;
    const stat = safeStat(stateFile);
    if (stat && stat.mtimeMs > bestMtime) {
      bestMtime = stat.mtimeMs;
      bestName = entry;
    }
  }

  return bestName;
}

// --- State reading ---

interface StoryState {
  story_context?: {
    story_direction?: string;
  };
  chapters?: Record<
    string,
    {
      scenes?: Record<string, any>;
      [key: string]: any;
    }
  >;
  characters?: Record<string, any>;
  plot_threads?: Record<string, { summary?: string; [key: string]: any }>;
}

function readState(storiesDir: string, storyName: string): StoryState | null {
  const statePath = join(storiesDir, storyName, "state.json");
  if (!isWithinBase(statePath, storiesDir)) return null;
  const raw = safeReadFile(statePath);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoryState;
  } catch {
    return null;
  }
}

// --- Wiki reading helpers ---

function readWikiPages(
  wikiDir: string,
  subdirName: string,
  storiesDir: string,
): Array<{ filename: string; metadata: Record<string, any>; body: string }> {
  const subdir = join(wikiDir, subdirName);
  if (!isWithinBase(subdir, storiesDir)) return [];
  const files = safeReadDir(subdir).filter((f) => f.endsWith(".md"));
  const pages: Array<{
    filename: string;
    metadata: Record<string, any>;
    body: string;
  }> = [];

  for (const file of files) {
    const filePath = join(subdir, file);
    if (!isWithinBase(filePath, storiesDir)) continue;
    const content = safeReadFile(filePath);
    if (!content) continue;
    const { metadata, body } = parseFrontmatter(content);
    pages.push({ filename: file.replace(/\.md$/, ""), metadata, body });
  }

  return pages;
}

// --- Current position extraction ---

function getCurrentPosition(state: StoryState): {
  chapter: number;
  scene: number;
} {
  const chapters = state.chapters || {};
  const chapterKeys = Object.keys(chapters)
    .map(Number)
    .filter((n) => !isNaN(n))
    .sort((a, b) => a - b);

  if (chapterKeys.length === 0) return { chapter: 0, scene: 0 };

  const lastChapter = chapterKeys[chapterKeys.length - 1];
  const chapterData = chapters[String(lastChapter)];
  const scenes = chapterData?.scenes || {};
  const sceneKeys = Object.keys(scenes)
    .map(Number)
    .filter((n) => !isNaN(n))
    .sort((a, b) => a - b);

  const lastScene =
    sceneKeys.length > 0 ? sceneKeys[sceneKeys.length - 1] : 0;
  return { chapter: lastChapter, scene: lastScene };
}

// --- Section builders ---

function buildCharactersSection(
  state: StoryState,
  wikiDir: string | null,
  storiesDir: string,
  budget: number,
): string {
  const lines: string[] = [];
  const wikiChars =
    wikiDir && isWithinBase(wikiDir, storiesDir)
      ? readWikiPages(wikiDir, "characters", storiesDir)
      : [];

  // Build lookup from wiki pages
  const wikiLookup = new Map<
    string,
    { role: string; summary: string }
  >();
  for (const page of wikiChars) {
    const name =
      page.metadata.title || page.metadata.slug || page.filename;
    const role = page.metadata.role || "unknown";
    const detailLevels = page.metadata.detail_levels || {};
    const summary = detailLevels.L1 || "";
    wikiLookup.set(name.toLowerCase(), { role, summary });
  }

  // State characters as base, enrich with wiki
  const stateChars = state.characters || {};
  const seen = new Set<string>();

  for (const key of Object.keys(stateChars)) {
    const lowerKey = key.toLowerCase();
    seen.add(lowerKey);
    const wiki = wikiLookup.get(lowerKey);
    const role = wiki?.role || "unknown";
    const summary = wiki?.summary || "";
    const line = summary
      ? `- **${key}** (${role}): ${summary}`
      : `- **${key}** (${role})`;
    lines.push(line);
  }

  // Add wiki-only characters not in state
  for (const page of wikiChars) {
    const name =
      page.metadata.title || page.metadata.slug || page.filename;
    if (seen.has(name.toLowerCase())) continue;
    const role = page.metadata.role || "unknown";
    const detailLevels = page.metadata.detail_levels || {};
    const summary = detailLevels.L1 || "";
    const line = summary
      ? `- **${name}** (${role}): ${summary}`
      : `- **${name}** (${role})`;
    lines.push(line);
  }

  // Truncate to budget
  let result = lines.join("\n");
  while (estimateTokens(result) > budget && lines.length > 1) {
    lines.pop();
    result = lines.join("\n");
  }

  return result;
}

function buildPlotThreadsSection(
  state: StoryState,
  wikiDir: string | null,
  storiesDir: string,
  budget: number,
): string {
  const lines: string[] = [];
  const wikiThreads =
    wikiDir && isWithinBase(wikiDir, storiesDir)
      ? readWikiPages(wikiDir, "plot-threads", storiesDir)
      : [];

  // Wiki lookup
  const wikiLookup = new Map<
    string,
    { status: string; summary: string }
  >();
  for (const page of wikiThreads) {
    const name =
      page.metadata.title || page.metadata.slug || page.filename;
    const status = page.metadata.status || "active";
    const detailLevels = page.metadata.detail_levels || {};
    const summary = detailLevels.L2 || detailLevels.L1 || "";
    wikiLookup.set(name.toLowerCase(), { status, summary });
  }

  // State threads as base
  const stateThreads = state.plot_threads || {};
  const seen = new Set<string>();

  for (const [key, val] of Object.entries(stateThreads)) {
    const lowerKey = key.toLowerCase();
    seen.add(lowerKey);
    const wiki = wikiLookup.get(lowerKey);
    const status = wiki?.status || "active";
    const summary = wiki?.summary || val?.summary || "";
    const line = summary
      ? `- **${key}** (${status}): ${summary}`
      : `- **${key}** (${status})`;
    lines.push(line);
  }

  // Wiki-only threads
  for (const page of wikiThreads) {
    const name =
      page.metadata.title || page.metadata.slug || page.filename;
    if (seen.has(name.toLowerCase())) continue;
    const status = page.metadata.status || "active";
    const detailLevels = page.metadata.detail_levels || {};
    const summary = detailLevels.L2 || detailLevels.L1 || "";
    const line = summary
      ? `- **${name}** (${status}): ${summary}`
      : `- **${name}** (${status})`;
    lines.push(line);
  }

  let result = lines.join("\n");
  while (estimateTokens(result) > budget && lines.length > 1) {
    lines.pop();
    result = lines.join("\n");
  }

  return result;
}

function buildSynopsesSection(
  wikiDir: string | null,
  storiesDir: string,
  budget: number,
): string {
  if (!wikiDir || !isWithinBase(wikiDir, storiesDir)) return "";

  const chapterPages = readWikiPages(wikiDir, "chapters", storiesDir);
  if (chapterPages.length === 0) return "";

  // Sort by filename (chapter-01, chapter-02, etc.)
  chapterPages.sort((a, b) => a.filename.localeCompare(b.filename));

  // Take last 2 chapters
  const recentChapters = chapterPages.slice(-2);
  const sections: string[] = [];

  for (const page of recentChapters) {
    const title = page.metadata.title || page.filename;
    const detailLevels = page.metadata.detail_levels || {};
    let synopsis = detailLevels.L2 || detailLevels.L1 || "";

    // Fallback to L1 if over budget
    if (estimateTokens(synopsis) > budget / 2 && detailLevels.L1) {
      synopsis = detailLevels.L1;
    }

    if (synopsis) {
      sections.push(`#### ${title}\n${synopsis}`);
    }
  }

  let result = sections.join("\n\n");
  while (estimateTokens(result) > budget && sections.length > 1) {
    sections.shift();
    result = sections.join("\n\n");
  }

  return result;
}

// --- Main context assembly ---

function assembleContext(
  storiesDir: string,
  storyName: string,
): string | null {
  const state = readState(storiesDir, storyName);
  if (!state) return null;

  const wikiDir = join(storiesDir, storyName, "wiki");
  const wikiExists =
    isWithinBase(wikiDir, storiesDir) && safeReadDir(wikiDir).length > 0;
  const effectiveWikiDir = wikiExists ? wikiDir : null;

  const position = getCurrentPosition(state);
  const storyDirection = state.story_context?.story_direction || "";

  // Budget allocation (~4000 tokens total)
  const DIRECTION_BUDGET = 200;
  const CHAR_BUDGET = 800;
  const THREAD_BUDGET = 800;
  const SYNOPSIS_BUDGET = 2000;

  // Build sections
  const sections: string[] = ["## Story Continuity Context"];

  // Current Position
  if (position.chapter > 0) {
    sections.push(
      `\n### Current Position\nChapter ${position.chapter}, Scene ${position.scene}`,
    );
  }

  // Story Direction
  if (storyDirection) {
    let direction = storyDirection;
    if (estimateTokens(direction) > DIRECTION_BUDGET) {
      direction = direction.slice(0, DIRECTION_BUDGET * 4);
    }
    sections.push(`\n### Story Direction\n${direction}`);
  }

  // Characters
  const charsText = buildCharactersSection(
    state,
    effectiveWikiDir,
    storiesDir,
    CHAR_BUDGET,
  );
  if (charsText) {
    sections.push(`\n### Active Characters\n${charsText}`);
  }

  // Plot Threads
  const threadsText = buildPlotThreadsSection(
    state,
    effectiveWikiDir,
    storiesDir,
    THREAD_BUDGET,
  );
  if (threadsText) {
    sections.push(`\n### Active Plot Threads\n${threadsText}`);
  }

  // Recent Chapter Synopses
  const synopsesText = buildSynopsesSection(
    effectiveWikiDir,
    storiesDir,
    SYNOPSIS_BUDGET,
  );
  if (synopsesText) {
    sections.push(`\n### Recent Chapter Synopses\n${synopsesText}`);
  }

  // Only header present — nothing useful to inject
  if (sections.length <= 1) return null;

  let result = sections.join("\n");

  // Final token check — progressive truncation
  if (estimateTokens(result) > 4000) {
    // Rebuild with tighter budgets
    const tightSections: string[] = ["## Story Continuity Context"];

    if (position.chapter > 0) {
      tightSections.push(
        `\n### Current Position\nChapter ${position.chapter}, Scene ${position.scene}`,
      );
    }
    if (storyDirection) {
      tightSections.push(
        `\n### Story Direction\n${storyDirection.slice(0, 400)}`,
      );
    }

    const tightChars = buildCharactersSection(
      state,
      effectiveWikiDir,
      storiesDir,
      400,
    );
    if (tightChars) {
      tightSections.push(`\n### Active Characters\n${tightChars}`);
    }

    const tightThreads = buildPlotThreadsSection(
      state,
      effectiveWikiDir,
      storiesDir,
      400,
    );
    if (tightThreads) {
      tightSections.push(`\n### Active Plot Threads\n${tightThreads}`);
    }

    // Synopses at L1 only — handled internally by buildSynopsesSection budget
    const tightSynopses = buildSynopsesSection(
      effectiveWikiDir,
      storiesDir,
      800,
    );
    if (tightSynopses) {
      tightSections.push(
        `\n### Recent Chapter Synopses\n${tightSynopses}`,
      );
    }

    result = tightSections.join("\n");
  }

  return result;
}

// --- Named exports for testing ---
export {
  parseFrontmatter,
  unquote,
  estimateTokens,
  isWithinBase,
  getCurrentPosition,
  assembleContext,
};
export type { StoryState };

// --- Plugin API interfaces ---
// Local type definitions for the OpenCode plugin API boundary.
// These reflect the observed runtime contract — no published SDK types exist.

/** Context object provided by OpenCode to plugin entry point. */
interface PluginContext {
  directory?: string;
  worktree?: string;
}

/** Input parameter for the compaction hook (currently unused). */
interface CompactionInput {}

/** Output parameter for the compaction hook — append context blocks here. */
interface CompactionOutput {
  context: string[];
}

// --- Plugin export ---

export default async (ctx: PluginContext) => {
  return {
    "experimental.session.compacting": async (
      _input: CompactionInput,
      output: CompactionOutput,
    ) => {
      try {
        const projectRoot: string = ctx.directory || ctx.worktree || "";
        if (!projectRoot) return;

        const storiesDir = resolve(projectRoot, "stories");
        const storyName = detectStory(storiesDir);
        if (!storyName) return;

        const contextBlock = assembleContext(storiesDir, storyName);
        if (!contextBlock) return;

        output.context.push(contextBlock);
      } catch {
        // Never crash the plugin — OpenCode continues regardless
      }
    },
  };
};
