import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Assemble completed chapter savepoints into a single story markdown file, or generate a chapter handoff artifact.",
  args: {
    operation: z
      .enum(["assemble", "generate-handoff"])
      .describe("Operation to perform"),
    storyName: z.string().describe("Story name (directory under stories/)"),
    chapterNum: z
      .number()
      .int()
      .optional()
      .describe("Chapter number (required for generate-handoff)"),
    model: z.string().optional().describe("Model override (generate-handoff only)"),
  },
  execute: async ({
    operation,
    storyName,
    chapterNum,
    model,
  }: {
    operation: "assemble" | "generate-handoff";
    storyName: string;
    chapterNum?: number;
    model?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/story_assembler.py",
      operation,
      "--story-name",
      storyName,
    ];

    if (operation === "generate-handoff") {
      if (chapterNum === undefined) {
        return "Error: chapterNum is required for generate-handoff operation";
      }
      args.push("--chapter-num", String(chapterNum));
      if (model) {
        args.push("--model", model);
      }
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
          ? parts.join("\n")
          : execError.message || "Unknown error";
      return `Error: ${errorMessage}`;
    }
  },
});
