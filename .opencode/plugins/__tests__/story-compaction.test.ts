import { describe, expect, it } from "vitest";
import {
  parseFrontmatter,
  unquote,
  estimateTokens,
  isWithinBase,
  getCurrentPosition,
} from "../story-compaction";
import type { StoryState } from "../story-compaction";

// --- parseFrontmatter ---

describe("parseFrontmatter", () => {
  it("parses normal YAML frontmatter with multiple key-value pairs", () => {
    const content = `---
title: My Story
slug: my-story
role: protagonist
---
Body content here.`;
    const { metadata, body } = parseFrontmatter(content);
    expect(metadata).toEqual({
      title: "My Story",
      slug: "my-story",
      role: "protagonist",
    });
    expect(body).toBe("Body content here.");
  });

  it("returns empty metadata and body for empty frontmatter block", () => {
    const content = `---
---
Body after empty frontmatter.`;
    const { metadata, body } = parseFrontmatter(content);
    expect(metadata).toEqual({});
    expect(body).toBe("Body after empty frontmatter.");
  });

  it("returns empty metadata and full content when no frontmatter present", () => {
    const content = "Just some plain text\nwith multiple lines.";
    const { metadata, body } = parseFrontmatter(content);
    expect(metadata).toEqual({});
    expect(body).toBe(content);
  });

  it("handles nested keys with indentation (dot-notation style nesting)", () => {
    const content = `---
detail_levels:
  L1: short summary
  L2: longer summary with more detail
---
Body text.`;
    const { metadata, body } = parseFrontmatter(content);
    expect(metadata.detail_levels).toEqual({
      L1: "short summary",
      L2: "longer summary with more detail",
    });
    expect(body).toBe("Body text.");
  });

  it("unquotes single-quoted values", () => {
    const content = `---
title: 'My Story'
---
Body.`;
    const { metadata } = parseFrontmatter(content);
    expect(metadata.title).toBe("My Story");
  });

  it("unquotes double-quoted values", () => {
    const content = `---
title: "My Story"
---
Body.`;
    const { metadata } = parseFrontmatter(content);
    expect(metadata.title).toBe("My Story");
  });

  it("treats content as no-frontmatter when closing --- is missing", () => {
    // split("---") yields fewer than 3 parts when there's only one ---
    // Actually: "---\ntitle: X\nbody" → split("---") → ["", "\ntitle: X\nbody"]
    // That's length 2, so falls into the < 3 branch → returns empty metadata + full content
    const content = `---
title: X
body text without closing`;
    const { metadata, body } = parseFrontmatter(content);
    expect(metadata).toEqual({});
    expect(body).toBe(content);
  });

  it("preserves body containing --- separators after frontmatter", () => {
    const content = `---
title: Test
---
Body with --- separator --- in it.`;
    const { metadata, body } = parseFrontmatter(content);
    expect(metadata.title).toBe("Test");
    expect(body).toBe("Body with --- separator --- in it.");
  });
});

// --- unquote ---

describe("unquote", () => {
  it("returns unquoted value as-is", () => {
    expect(unquote("hello")).toBe("hello");
  });

  it("removes single quotes", () => {
    expect(unquote("'hello'")).toBe("hello");
  });

  it("removes double quotes", () => {
    expect(unquote('"hello"')).toBe("hello");
  });

  it("returns empty string as-is", () => {
    expect(unquote("")).toBe("");
  });
});

// --- estimateTokens ---

describe("estimateTokens", () => {
  it("returns 0 for empty string", () => {
    expect(estimateTokens("")).toBe(0);
  });

  it("returns 1 for string of length 1", () => {
    expect(estimateTokens("a")).toBe(1);
  });

  it("returns 1 for string of length 4", () => {
    expect(estimateTokens("abcd")).toBe(1);
  });

  it("returns 2 for string of length 5", () => {
    expect(estimateTokens("abcde")).toBe(2);
  });

  it("computes Math.ceil(length / 4) for known-length string", () => {
    const text = "a".repeat(100);
    expect(estimateTokens(text)).toBe(25);
  });
});

// --- isWithinBase ---

describe("isWithinBase", () => {
  it("returns true for valid child path", () => {
    expect(isWithinBase("/base/child/file.txt", "/base")).toBe(true);
  });

  it("returns false for ../ traversal", () => {
    expect(isWithinBase("/base/../etc/passwd", "/base")).toBe(false);
  });

  it("returns true for exact base match", () => {
    expect(isWithinBase("/base", "/base")).toBe(true);
  });

  it("returns false for completely different path", () => {
    expect(isWithinBase("/other/path", "/base")).toBe(false);
  });

  it("returns false for partial prefix match (not a real child)", () => {
    // /base-extra is not within /base
    expect(isWithinBase("/base-extra/file.txt", "/base")).toBe(false);
  });
});

// --- getCurrentPosition ---

describe("getCurrentPosition", () => {
  it("returns correct chapter and scene for state with multiple chapters", () => {
    const state: StoryState = {
      chapters: {
        "1": { scenes: { "1": {}, "2": {} } },
        "2": { scenes: { "1": {}, "2": {}, "3": {} } },
        "3": { scenes: { "1": {} } },
      },
    };
    const pos = getCurrentPosition(state);
    expect(pos).toEqual({ chapter: 3, scene: 1 });
  });

  it("returns scene 0 when last chapter has no scenes", () => {
    const state: StoryState = {
      chapters: {
        "1": { scenes: { "1": {} } },
        "2": {},
      },
    };
    const pos = getCurrentPosition(state);
    expect(pos).toEqual({ chapter: 2, scene: 0 });
  });

  it("returns { chapter: 0, scene: 0 } for empty chapters", () => {
    const state: StoryState = { chapters: {} };
    const pos = getCurrentPosition(state);
    expect(pos).toEqual({ chapter: 0, scene: 0 });
  });

  it("returns { chapter: 0, scene: 0 } when chapters is undefined", () => {
    const state: StoryState = {};
    const pos = getCurrentPosition(state);
    expect(pos).toEqual({ chapter: 0, scene: 0 });
  });
});
