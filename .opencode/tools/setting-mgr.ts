import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Manage story setting sheets: extract-names, generate-sheet, update-sheet, load-sheet, list, or generate-abridged. Setting sheets are stored as JSON files in stories/<name>/settings/.",
  args: {
    operation: z
      .enum([
        "extract-names",
        "generate-sheet",
        "update-sheet",
        "load-sheet",
        "list",
        "generate-abridged",
      ])
      .describe("Operation to perform"),
    name: z.string().describe("Story name (directory under stories/)"),
    setting: z
      .string()
      .optional()
      .describe(
        "Setting name (required for all operations except list and extract-names)"
      ),
    data: z
      .string()
      .optional()
      .describe(
        "JSON string input (required for extract-names, update-sheet; optional escape hatch for generate-sheet)"
      ),
    additionalContext: z
      .string()
      .optional()
      .describe(
        "Extra context to inject into setting generation prompt (generate-sheet only)"
      ),
    model: z
      .string()
      .optional()
      .describe("LLM model name for generate-sheet"),
    budget: z
      .number()
      .optional()
      .describe("Word budget for generate-abridged (default: 500)"),
    abridged: z
      .boolean()
      .optional()
      .describe("If true, load-sheet returns abridged version only"),
  },
  execute: async ({
    operation,
    name,
    setting,
    data,
    additionalContext,
    model,
    budget,
    abridged,
  }: {
    operation: string;
    name: string;
    setting?: string;
    data?: string;
    additionalContext?: string;
    model?: string;
    budget?: number;
    abridged?: boolean;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/setting_manager.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (setting) {
      args.push("--setting", setting);
    }
    if (data !== undefined) {
      args.push("--data", data);
    }
    if (additionalContext !== undefined) {
      args.push("--additional-context", additionalContext);
    }
    if (model !== undefined) {
      args.push("--model", model);
    }
    if (budget !== undefined) {
      args.push("--budget", String(budget));
    }
    if (abridged) {
      args.push("--abridged");
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
