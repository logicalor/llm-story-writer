import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { describe, expect, it, afterEach } from "vitest";
import { assembleContext } from "../story-compaction";

describe("assembleContext", () => {
  const tempDirs: string[] = [];

  function makeTempStoriesDir(): string {
    const dir = mkdtempSync(join(tmpdir(), "sc-test-"));
    tempDirs.push(dir);
    return dir;
  }

  afterEach(() => {
    for (const dir of tempDirs) {
      rmSync(dir, { recursive: true, force: true });
    }
    tempDirs.length = 0;
  });

  it("assembles context from state and wiki pages (happy path)", () => {
    const storiesDir = makeTempStoriesDir();
    const storyDir = join(storiesDir, "test-story");
    mkdirSync(storyDir, { recursive: true });

    // state.json
    const state = {
      story_context: { story_direction: "The hero embarks on a quest." },
      chapters: {
        "1": { scenes: { "1": {}, "2": {} } },
        "2": { scenes: { "1": {} } },
      },
      characters: { Alice: { role: "protagonist" } },
      plot_threads: { "Main Quest": { summary: "Find the artifact." } },
    };
    writeFileSync(join(storyDir, "state.json"), JSON.stringify(state));

    // Wiki directories
    const wikiDir = join(storyDir, "wiki");
    mkdirSync(join(wikiDir, "characters"), { recursive: true });
    mkdirSync(join(wikiDir, "plot-threads"), { recursive: true });
    mkdirSync(join(wikiDir, "chapters"), { recursive: true });

    // Character wiki page
    writeFileSync(
      join(wikiDir, "characters", "alice.md"),
      `---
title: Alice
role: protagonist
detail_levels:
  L1: A brave adventurer
---
Full character bio here.`,
    );

    // Plot thread wiki page
    writeFileSync(
      join(wikiDir, "plot-threads", "main-quest.md"),
      `---
title: Main Quest
status: active
detail_levels:
  L1: Find the lost artifact
  L2: The ancient artifact was hidden in the Caves of Sorrow
---
Thread details here.`,
    );

    // Chapter wiki page
    writeFileSync(
      join(wikiDir, "chapters", "chapter-1.md"),
      `---
title: Chapter 1
detail_levels:
  L1: Alice begins her journey
  L2: Alice leaves the village and enters the dark forest
---
Chapter synopsis body.`,
    );

    const result = assembleContext(storiesDir, "test-story");
    expect(result).not.toBeNull();
    expect(result).toContain("## Story Continuity Context");
    expect(result).toContain("Chapter 2, Scene 1");
    expect(result).toContain("The hero embarks on a quest.");
    expect(result).toContain("Alice");
    expect(result).toContain("Main Quest");
    expect(result).toContain("Chapter 1");
    expect(result).toContain("brave adventurer");
  });

  it("returns context without wiki sections when wiki directory is missing", () => {
    const storiesDir = makeTempStoriesDir();
    const storyDir = join(storiesDir, "test-story");
    mkdirSync(storyDir, { recursive: true });

    const state = {
      story_context: { story_direction: "Direction text." },
      chapters: { "1": { scenes: { "1": {} } } },
      characters: { Bob: {} },
      plot_threads: { "Side Quest": { summary: "Optional task." } },
    };
    writeFileSync(join(storyDir, "state.json"), JSON.stringify(state));

    const result = assembleContext(storiesDir, "test-story");
    expect(result).not.toBeNull();
    expect(result).toContain("## Story Continuity Context");
    expect(result).toContain("Chapter 1, Scene 1");
    expect(result).toContain("Direction text.");
    expect(result).toContain("Bob");
    expect(result).toContain("Side Quest");
  });

  it("returns null when state.json is missing", () => {
    const storiesDir = makeTempStoriesDir();
    const storyDir = join(storiesDir, "test-story");
    mkdirSync(storyDir, { recursive: true });
    // No state.json

    const result = assembleContext(storiesDir, "test-story");
    expect(result).toBeNull();
  });

  it("returns null when state.json contains invalid JSON", () => {
    const storiesDir = makeTempStoriesDir();
    const storyDir = join(storiesDir, "test-story");
    mkdirSync(storyDir, { recursive: true });
    writeFileSync(join(storyDir, "state.json"), "not valid json {{{");

    const result = assembleContext(storiesDir, "test-story");
    expect(result).toBeNull();
  });
});
