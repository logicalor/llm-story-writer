import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  description:
    "Manage story character sheets: extract-names, generate-sheet, update-sheet, load-sheet, list, or generate-abridged. Character sheets are stored as JSON files in stories/<name>/characters/.",
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
    character: z
      .string()
      .optional()
      .describe(
        "Character name (required for all operations except list and extract-names)"
      ),
    data: z
      .string()
      .optional()
      .describe(
        "JSON string input (required for extract-names, generate-sheet, update-sheet)"
      ),
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
    character,
    data,
    budget,
    abridged,
  }: {
    operation: string;
    name: string;
    character?: string;
    data?: string;
    budget?: number;
    abridged?: boolean;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/character_manager.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (character) {
      args.push("--character", character);
    }
    if (data !== undefined) {
      args.push("--data", data);
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
};
