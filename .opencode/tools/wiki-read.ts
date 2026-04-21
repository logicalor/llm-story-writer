import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Read wiki pages by slug, type, or glob pattern with configurable detail levels (headline/brief/full), or match entity names in text against the wiki index.",
  args: {
    operation: z
      .enum(["read", "match-entities"])
      .describe("Operation to perform"),
    name: z.string().describe("Story name (directory under stories/)"),
    slug: z.string().optional().describe("Page slug to read"),
    type: z.string().optional().describe("Page type to filter by (e.g., character, location, event)"),
    glob: z.string().optional().describe("Glob pattern for page matching"),
    detailLevel: z
      .enum(["headline", "brief", "full"])
      .optional()
      .describe("Detail level for returned content (default: brief)"),
    text: z
      .string()
      .optional()
      .describe("Text to match entities against (required for match-entities)"),
  },
  execute: async ({
    operation,
    name,
    slug,
    type,
    glob,
    detailLevel,
    text,
  }: {
    operation: string;
    name: string;
    slug?: string;
    type?: string;
    glob?: string;
    detailLevel?: string;
    text?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/wiki_read.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (slug) {
      args.push("--slug", slug);
    }
    if (type) {
      args.push("--type", type);
    }
    if (glob) {
      args.push("--glob", glob);
    }
    if (detailLevel) {
      args.push("--detail-level", detailLevel);
    }
    if (text) {
      args.push("--text", text);
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
