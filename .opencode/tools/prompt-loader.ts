import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Load a prompt template by ID and substitute variables. Returns the rendered prompt text.",
  args: {
    promptId: z
      .string()
      .describe("Prompt template ID (e.g., 'chapters/create_content')"),
    variables: z
      .record(z.string(), z.string())
      .optional()
      .describe("Key-value pairs to substitute in the template"),
  },
  execute: async ({
    promptId,
    variables,
  }: {
    promptId: string;
    variables?: Record<string, string>;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = ["src/tools/prompt_loader.py", "--prompt-id", promptId];

    if (variables && Object.keys(variables).length > 0) {
      args.push("--variables", JSON.stringify(variables));
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
