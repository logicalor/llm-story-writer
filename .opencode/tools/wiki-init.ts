import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Initialise a story wiki directory structure with subdirectories, schema template, index, log, and contradictions files. Idempotent — safe to call if wiki already exists.",
  args: {
    operation: z.enum(["init"]).describe("Operation to perform"),
    name: z.string().describe("Story name (directory under stories/)"),
  },
  execute: async ({
    operation,
    name,
  }: {
    operation: "init";
    name: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/wiki_init.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

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
