import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Manage chapter recaps: load, generate (5-stage pipeline), sanitize, or compact. Recaps are JSON event timelines stored as savepoints under stories/<name>/savepoints/chapter_N/recap.",
  args: {
    operation: z
      .enum(["load", "generate", "sanitize", "compact"])
      .describe("Operation to perform"),
    name: z.string().describe("Story name (directory under stories/)"),
    chapter: z.number().describe("Chapter number"),
    storyStartDate: z
      .string()
      .optional()
      .describe(
        "Story start date in YYYY-MM-DD format (required for generate and sanitize)"
      ),
    enableProgrammaticClassification: z
      .boolean()
      .optional()
      .describe(
        "Enable programmatic recency classification during sanitize (default: false)"
      ),
    model: z
      .string()
      .optional()
      .describe("Override LLM model identifier"),
  },
  execute: async ({
    operation,
    name,
    chapter,
    storyStartDate,
    enableProgrammaticClassification,
    model,
  }: {
    operation: string;
    name: string;
    chapter: number;
    storyStartDate?: string;
    enableProgrammaticClassification?: boolean;
    model?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/recap_manager.py",
      "--operation",
      operation,
      "--name",
      name,
      "--chapter",
      String(chapter),
    ];

    if (storyStartDate) {
      args.push("--story-start-date", storyStartDate);
    }
    if (enableProgrammaticClassification) {
      args.push("--enable-programmatic-classification");
    }
    if (model) {
      args.push("--model", model);
    }

    try {
      const stdout = execFileSync("python3", args, {
        cwd: projectRoot,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      });
      return stdout.trim();
    } catch (error: unknown) {
      const execError = error as {
        stdout?: string;
        stderr?: string;
        message?: string;
      };
      const parts = [
        execError.stderr?.trim(),
        execError.stdout?.trim(),
      ].filter(Boolean) as string[];
      const errorMessage =
        parts.length > 0
          ? parts.join("
")
          : execError.message || "Unknown error";
      return `Error: ${errorMessage}`;
    }
  },
});
