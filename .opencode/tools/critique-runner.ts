import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Run critics against story content, parse scores, check quality thresholds, and generate feedback",
  args: {
    operation: z
      .enum([
        "run-critics",
        "parse-scores",
        "should-refine",
        "generate-feedback",
        "run-arc-analysis",
      ])
      .describe("Operation to perform"),
    name: z
      .string()
      .optional()
      .describe(
        "Story name (required for run-critics, should-refine, generate-feedback)"
      ),
    iteration: z
      .number()
      .optional()
      .describe("Critique iteration number (default: 1)"),
    content: z
      .string()
      .optional()
      .describe("Content to critique (if not loading from savepoint)"),
    mode: z
      .enum(["outline", "chapter", "character-voice"])
      .optional()
      .describe("Critique mode: outline, chapter, or character-voice (default: outline)"),
    criticType: z
      .string()
      .optional()
      .describe("Critic type for parse-scores"),
    responseText: z
      .string()
      .optional()
      .describe("Raw critic response text for parse-scores"),
    qualityThreshold: z
      .number()
      .optional()
      .describe("Quality threshold for should-refine (default: 85.0)"),
    criterionFloor: z
      .number()
      .optional()
      .describe(
        "Minimum per-criterion score percentage for should-refine (default: 75.0)"
      ),
    model: z.string().optional().describe("Override LLM model identifier"),
    criticSummary: z
      .string()
      .optional()
      .describe("Optional critic summary for arc synthesis (run-arc-analysis)"),
  },
  execute: async ({
    operation,
    name,
    iteration,
    content,
    mode,
    criticType,
    responseText,
    qualityThreshold,
    criterionFloor,
    model,
    criticSummary,
  }: {
    operation: string;
    name?: string;
    iteration?: number;
    content?: string;
    mode?: string;
    criticType?: string;
    responseText?: string;
    qualityThreshold?: number;
    criterionFloor?: number;
    model?: string;
    criticSummary?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/critique_runner.py",
      "--operation",
      operation,
    ];

    if (name) {
      args.push("--name", name);
    }
    if (iteration !== undefined) {
      args.push("--iteration", String(iteration));
    }
    if (content) {
      args.push("--content", content);
    }
    if (mode) {
      args.push("--mode", mode);
    }
    if (criticType) {
      args.push("--critic-type", criticType);
    }
    if (responseText) {
      args.push("--response-text", responseText);
    }
    if (qualityThreshold !== undefined) {
      args.push("--quality-threshold", String(qualityThreshold));
    }
    if (criterionFloor !== undefined) {
      args.push("--criterion-floor", String(criterionFloor));
    }
    if (model) {
      args.push("--model", model);
    }
    if (criticSummary !== undefined) {
      args.push("--critic-summary", criticSummary);
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
