import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Manage story state: init, read, write, or list stories. Handles story_context, characters, plot_threads, and chapters.",
  args: {
    operation: z
      .enum(["init", "read", "write", "list"])
      .describe("Operation to perform"),
    name: z.string().optional().describe("Story name"),
    field: z
      .string()
      .optional()
      .describe("Dot-notation field path (e.g., 'story_context.tone_style')"),
    value: z
      .string()
      .optional()
      .describe(
        "JSON string value for write operation. Pass '-' to read from stdin (use with heredoc for values containing quotes or apostrophes).",
      ),
  },
  execute: async ({
    operation,
    name,
    field,
    value,
  }: {
    operation: "init" | "read" | "write" | "list";
    name?: string;
    field?: string;
    value?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = ["src/tools/story_state.py", "--operation", operation];

    if (name) {
      args.push("--name", name);
    }
    if (field) {
      args.push("--field", field);
    }
    if (value !== undefined) {
      args.push("--value", value);
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
