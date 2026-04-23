import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { resolve } from "path";
import { runTool } from "../_run";

export default tool({
  description:
    "Manage story savepoints: save, load, has, list, list-full, clear, or next-phase. Use 'list' (names only, fast) for resume/discovery — NOT 'list-full' (dumps all data, wastes tokens). Use 'next-phase' (preferred for /continue) to get the deterministic resume target. Supports hierarchical step paths like chapter_1/scene_2. Python script: src/tools/savepoint_manager.py.",
  args: {
    operation: z
      .enum([
        "save",
        "load",
        "has",
        "list",
        "list-full",
        "clear",
        "next-phase",
      ])
      .describe(
        "Operation. 'list' returns names only (fast, preferred). 'list-full' returns names + data (large, avoid unless needed). 'next-phase' returns the deterministic resume target."
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
    operation:
      | "save"
      | "load"
      | "has"
      | "list"
      | "list-full"
      | "clear"
      | "next-phase";
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

    return runTool("src/tools/savepoint_manager.py", args, { cwd: projectRoot });
  },
});
