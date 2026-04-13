import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  name: "savepoint-mgr",
  description:
    "Manage story savepoints: save, load, has, list, or clear. Supports hierarchical step paths like chapter_1/scene_2.",
  parameters: z.object({
    operation: z
      .enum(["save", "load", "has", "list", "clear"])
      .describe("Operation to perform"),
    name: z.string().describe("Story name"),
    step: z
      .string()
      .optional()
      .describe(
        "Step name (required for save/load/has). Supports hierarchical paths like chapter_1/scene_2"
      ),
    data: z
      .string()
      .optional()
      .describe("Data to save (JSON string, required for save operation)"),
  }),
  execute: async ({
    operation,
    name,
    step,
    data,
  }: {
    operation: "save" | "load" | "has" | "list" | "clear";
    name: string;
    step?: string;
    data?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/savepoint_manager.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (step) {
      args.push("--step", step);
    }
    if (data !== undefined) {
      args.push("--data", data);
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
