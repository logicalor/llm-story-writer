import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  description:
    "Assemble completed chapter savepoints into a single story markdown file.",
  args: {
    storyName: z.string().describe("Story name (directory under stories/)")
  },
  execute: async ({
    storyName,
  }: {
    storyName: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/story_assembler.py",
      "assemble",
      "--story-name",
      storyName,
    ];

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