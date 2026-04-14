import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  name: "critique-runner",
  description:
    "Run critics against story content, parse scores, check quality thresholds, and generate feedback",
  parameters: z.object({
    operation: z
      .enum(["run-critics", "parse-scores", "should-refine", "generate-feedback"])
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
    model: z.string().optional().describe("Override LLM model identifier"),
  }),
  execute: async ({
    operation,
    name,
    iteration,
    content,
    criticType,
    responseText,
    qualityThreshold,
    model,
  }: {
    operation: string;
    name?: string;
    iteration?: number;
    content?: string;
    criticType?: string;
    responseText?: string;
    qualityThreshold?: number;
    model?: string;
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
    if (criticType) {
      args.push("--critic-type", criticType);
    }
    if (responseText) {
      args.push("--response-text", responseText);
    }
    if (qualityThreshold !== undefined) {
      args.push("--quality-threshold", String(qualityThreshold));
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
      const execError = error as { stderr?: string; message?: string };
      const message =
        execError.stderr?.trim() || execError.message || "Unknown error";
      return `Error: ${message}`;
    }
  },
};
