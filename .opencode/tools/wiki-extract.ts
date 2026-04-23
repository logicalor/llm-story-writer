import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { runTool } from "../_run";

export default tool({
  description:
    "Extract wiki entities and wiki batch payloads from outlines, sheets, and completed chapters. Handles entity extraction, detail-level generation, and optional batch application.",
  args: {
    operation: z
      .enum(["initial-populate", "update-from-chapter"])
      .describe("Extraction operation to perform"),
    name: z.string().describe("Story name (directory under stories/ )"),
    chapterNumber: z
      .number()
      .optional()
      .describe("Chapter number for update-from-chapter"),
    chapterTextPath: z
      .string()
      .optional()
      .describe("Path to chapter text file for update-from-chapter"),
    model: z.string().optional().describe("Override model name"),
    apply: z
      .boolean()
      .default(true)
      .describe("Apply the assembled wiki batch. False returns dry-run payload."),
  },
  execute: async ({
    operation,
    name,
    chapterNumber,
    chapterTextPath,
    model,
    apply,
  }: {
    operation: "initial-populate" | "update-from-chapter";
    name: string;
    chapterNumber?: number;
    chapterTextPath?: string;
    model?: string;
    apply?: boolean;
  }) => {
    const args = [operation, "--name", name];

    if (operation === "update-from-chapter") {
      if (chapterNumber === undefined) {
        return "Error: chapterNumber is required for update-from-chapter";
      }
      if (!chapterTextPath) {
        return "Error: chapterTextPath is required for update-from-chapter";
      }
      args.push("--chapter-number", String(chapterNumber));
      args.push("--chapter-text-path", chapterTextPath);
    }

    if (model) {
      args.push("--model", model);
    }

    if (apply === false) {
      args.push("--dry-run");
    } else {
      args.push("--apply");
    }

    return runTool("src/tools/wiki_extract.py", args);
  },
});