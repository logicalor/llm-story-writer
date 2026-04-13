import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  name: "story-state",
  description:
    "Manage story state: init, read, write, or list stories. Handles story_context, characters, plot_threads, and chapters.",
  parameters: z.object({
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
      .describe("JSON string value for write operation"),
  }),
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
      const execError = error as { stderr?: string; message?: string };
      const message =
        execError.stderr?.trim() || execError.message || "Unknown error";
      return `Error: ${message}`;
    }
  },
};
