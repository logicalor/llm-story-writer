import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  description:
    "Assemble a pre-generation context snapshot for a scene. Uses three-stage hybrid retrieval (entity matching, metadata filtering, semantic search, wikilink traversal), token-budgeted detail levels, and structured markdown assembly.",
  args: {
    operation: z
      .enum(["snapshot", "cache-status"])
      .describe("Operation to perform"),
    name: z.string().describe("Story name"),
    chapter: z.number().int().positive().describe("Chapter number"),
    scene: z
      .number()
      .int()
      .positive()
      .optional()
      .describe("Scene number (required for snapshot)"),
    outline: z
      .string()
      .optional()
      .describe("Scene outline text (required for snapshot)"),
    povCharacter: z
      .string()
      .optional()
      .describe("POV character slug"),
    primaryLocation: z
      .string()
      .optional()
      .describe("Primary location slug"),
    characters: z
      .string()
      .optional()
      .describe("Comma-separated character slugs"),
    locations: z
      .string()
      .optional()
      .describe("Comma-separated location slugs"),
    sceneType: z
      .enum(["dialogue", "action", "exposition", "mixed"])
      .optional()
      .describe("Scene type for budget adaptation"),
    budget: z
      .number()
      .int()
      .positive()
      .optional()
      .describe("Token budget (default: 15000)"),
  },
  execute: async ({
    operation,
    name,
    chapter,
    scene,
    outline,
    povCharacter,
    primaryLocation,
    characters,
    locations,
    sceneType,
    budget,
  }: {
    operation: string;
    name: string;
    chapter: number;
    scene?: number;
    outline?: string;
    povCharacter?: string;
    primaryLocation?: string;
    characters?: string;
    locations?: string;
    sceneType?: string;
    budget?: number;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/wiki_snapshot.py",
      "--operation",
      operation,
      "--name",
      name,
      "--chapter",
      String(chapter),
    ];

    if (scene !== undefined) {
      args.push("--scene", String(scene));
    }
    if (outline) {
      args.push("--outline", outline);
    }
    if (povCharacter) {
      args.push("--pov-character", povCharacter);
    }
    if (primaryLocation) {
      args.push("--primary-location", primaryLocation);
    }
    if (characters) {
      args.push("--characters", characters);
    }
    if (locations) {
      args.push("--locations", locations);
    }
    if (sceneType) {
      args.push("--scene-type", sceneType);
    }
    if (budget !== undefined) {
      args.push("--budget", String(budget));
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
