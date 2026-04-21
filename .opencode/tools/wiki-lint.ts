import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Run consistency checks across the story wiki. Operations: check-chapter (post-chapter contradiction detection), check-full (comprehensive lint), check-entity (single entity validation).",
  args: {
    operation: z
      .enum(["check-chapter", "check-full", "check-entity"])
      .describe("Lint operation"),
    name: z.string().describe("Story name"),
    chapter_number: z
      .number()
      .optional()
      .describe("Chapter number (required for check-chapter)"),
    chapter_text: z
      .string()
      .optional()
      .describe("File path to chapter content (required for check-chapter)"),
    current_chapter: z
      .number()
      .optional()
      .describe("Current chapter number (required for check-full)"),
    slug: z
      .string()
      .optional()
      .describe("Entity slug (required for check-entity)"),
  },
  execute: async ({
    operation,
    name,
    chapter_number,
    chapter_text,
    current_chapter,
    slug,
  }: {
    operation: string;
    name: string;
    chapter_number?: number;
    chapter_text?: string;
    current_chapter?: number;
    slug?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/wiki_lint.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (chapter_number !== undefined) {
      args.push("--chapter-number", String(chapter_number));
    }
    if (chapter_text) {
      args.push("--chapter-text", chapter_text);
    }
    if (current_chapter !== undefined) {
      args.push("--current-chapter", String(current_chapter));
    }
    if (slug) {
      args.push("--slug", slug);
    }

    try {
      const stdout = execFileSync("python3", args, {
        cwd: projectRoot,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      return stdout.trim();
    } catch (error: unknown) {
      const execError = error as { stderr?: string; message?: string };
      const message =
        execError.stderr?.trim() || execError.message || "Unknown error";
      return `Error: ${message}`;
    }
  },
});
