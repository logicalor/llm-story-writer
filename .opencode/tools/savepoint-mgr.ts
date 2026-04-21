import { z } from "zod";
import { resolve } from "path";
import { runTool } from "./_run";

export default {
  description:
    "Manage story savepoints: save, load, has, list, list-full, or clear. Use 'list' (names only, fast) for resume/discovery — NOT 'list-full' (dumps all data, wastes tokens). Supports hierarchical step paths like chapter_1/scene_2. Python script: src/tools/savepoint_manager.py.",
  args: {
    operation: z
      .enum(["save", "load", "has", "list", "list-full", "clear"])
      .describe(
        "Operation. 'list' returns names only (fast, preferred). 'list-full' returns names + data (large, avoid unless needed)."
      ),
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
  },
  execute: async ({
    operation,
    name,
    step,
    data,
  }: {
    operation: "save" | "load" | "has" | "list" | "list-full" | "clear";
    name: string;
    step?: string;
    data?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
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

    return runTool("src/tools/savepoint_manager.py", args);
  },
};
