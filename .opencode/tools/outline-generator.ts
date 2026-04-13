import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  name: "outline-generator",
  description:
    "Outline generation pipeline: analyze story prompt (8-chunk analysis + start date + base context), generate story elements, generate initial outline, expand chapter chunks with continuity analysis, or refine outline with feedback.",
  parameters: z.object({
    operation: z
      .enum([
        "analyze-prompt",
        "generate-elements",
        "generate-outline",
        "expand-chapter",
        "refine",
      ])
      .describe("Operation to perform"),
    name: z.string().describe("Story name (directory under stories/)"),
    prompt: z
      .string()
      .optional()
      .describe(
        "Story prompt text (required for analyze-prompt, optional for generate-outline)"
      ),
    desiredChapters: z
      .number()
      .optional()
      .describe("Number of desired chapters (required for generate-outline)"),
    chunkStart: z
      .number()
      .optional()
      .describe("Start chapter for chunk expansion (required for expand-chapter)"),
    chunkEnd: z
      .number()
      .optional()
      .describe("End chapter for chunk expansion (required for expand-chapter)"),
    totalChapters: z
      .number()
      .optional()
      .describe(
        "Total chapters in story (required for expand-chapter)"
      ),
    previousChunks: z
      .string()
      .optional()
      .describe("Previous chunk outlines text (expand-chapter)"),
    continuitySummary: z
      .string()
      .optional()
      .describe("Continuity summary text (expand-chapter)"),
    feedback: z
      .string()
      .optional()
      .describe("Critique/feedback text (required for refine)"),
    model: z
      .string()
      .optional()
      .describe("Override LLM model identifier"),
  }),
  execute: async ({
    operation,
    name,
    prompt,
    desiredChapters,
    chunkStart,
    chunkEnd,
    totalChapters,
    previousChunks,
    continuitySummary,
    feedback,
    model,
  }: {
    operation: string;
    name: string;
    prompt?: string;
    desiredChapters?: number;
    chunkStart?: number;
    chunkEnd?: number;
    totalChapters?: number;
    previousChunks?: string;
    continuitySummary?: string;
    feedback?: string;
    model?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/outline_generator.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (prompt) {
      args.push("--prompt", prompt);
    }
    if (desiredChapters !== undefined) {
      args.push("--desired-chapters", String(desiredChapters));
    }
    if (chunkStart !== undefined) {
      args.push("--chunk-start", String(chunkStart));
    }
    if (chunkEnd !== undefined) {
      args.push("--chunk-end", String(chunkEnd));
    }
    if (totalChapters !== undefined) {
      args.push("--total-chapters", String(totalChapters));
    }
    if (previousChunks) {
      args.push("--previous-chunks", previousChunks);
    }
    if (continuitySummary) {
      args.push("--continuity-summary", continuitySummary);
    }
    if (feedback) {
      args.push("--feedback", feedback);
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
