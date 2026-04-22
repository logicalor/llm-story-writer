import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Scene writing pipeline: parse chapter outline into scene definitions, generate individual scenes, revise scenes with feedback, assemble scenes into a chapter, or analyze chapter prose for scrub and voice issues.",
  args: {
    operation: z
      .enum([
        "parse-definitions",
        "generate",
        "revise",
        "assemble-chapter",
        "scrub-analyze",
        "voice-analyze",
      ])
      .describe("Operation to perform"),
    name: z.string().describe("Story name (directory under stories/)"),
    chapterNum: z
      .number()
      .int()
      .min(1)
      .optional()
      .describe("Chapter number"),
    sceneNum: z
      .number()
      .int()
      .min(1)
      .optional()
      .describe("Scene number within the chapter"),
    sceneCount: z
      .number()
      .int()
      .min(1)
      .optional()
      .describe("Total number of scenes in the chapter (assemble-chapter)"),
    chapterOutline: z
      .string()
      .optional()
      .describe("Chapter outline text"),
    sceneDefinition: z
      .string()
      .optional()
      .describe("Scene definition as JSON string"),
    sceneContent: z
      .string()
      .optional()
      .describe("Current scene content (required for revise)"),
    feedback: z
      .string()
      .optional()
      .describe("Revision feedback (required for revise)"),
    chapterTitle: z
      .string()
      .optional()
      .describe("Chapter title (assemble-chapter, defaults to 'Chapter N')"),
    baseContext: z
      .string()
      .optional()
      .describe("Base story context"),
    storyElements: z
      .string()
      .optional()
      .describe("Story elements text"),
    characterSheets: z
      .string()
      .optional()
      .describe("Character sheets"),
    settingSheets: z
      .string()
      .optional()
      .describe("Setting sheets"),
    previousRecap: z
      .string()
      .optional()
      .describe("Previous chapter recap"),
    previousScene: z
      .string()
      .optional()
      .describe("Previous scene content"),
    nextSceneDefinition: z
      .string()
      .optional()
      .describe("Next scene definition"),
    nextChapterSynopsis: z
      .string()
      .optional()
      .describe("Next chapter synopsis"),
    model: z
      .string()
      .optional()
      .describe("Override LLM model identifier"),
    chapterText: z
      .string()
      .optional()
      .describe("Chapter text for scrub-analyze and voice-analyze operations"),
    priorChaptersSummary: z
      .string()
      .optional()
      .describe("Prior chapters summary for voice-analyze"),
  },
  execute: async ({
    operation,
    name,
    chapterNum,
    sceneNum,
    sceneCount,
    chapterOutline,
    sceneDefinition,
    sceneContent,
    feedback,
    chapterTitle,
    baseContext,
    storyElements,
    characterSheets,
    settingSheets,
    previousRecap,
    previousScene,
    nextSceneDefinition,
    nextChapterSynopsis,
    model,
    chapterText,
    priorChaptersSummary,
  }: {
    operation: string;
    name: string;
    chapterNum?: number;
    sceneNum?: number;
    sceneCount?: number;
    chapterOutline?: string;
    sceneDefinition?: string;
    sceneContent?: string;
    feedback?: string;
    chapterTitle?: string;
    baseContext?: string;
    storyElements?: string;
    characterSheets?: string;
    settingSheets?: string;
    previousRecap?: string;
    previousScene?: string;
    nextSceneDefinition?: string;
    nextChapterSynopsis?: string;
    model?: string;
    chapterText?: string;
    priorChaptersSummary?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/scene_writer.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (chapterNum !== undefined) {
      args.push("--chapter-num", String(chapterNum));
    }
    if (sceneNum !== undefined) {
      args.push("--scene-num", String(sceneNum));
    }
    if (sceneCount !== undefined) {
      args.push("--scene-count", String(sceneCount));
    }
    if (chapterOutline) {
      args.push("--chapter-outline", chapterOutline);
    }
    if (sceneDefinition) {
      args.push("--scene-definition", sceneDefinition);
    }
    if (sceneContent) {
      args.push("--scene-content", sceneContent);
    }
    if (feedback) {
      args.push("--feedback", feedback);
    }
    if (chapterTitle) {
      args.push("--chapter-title", chapterTitle);
    }
    if (baseContext) {
      args.push("--base-context", baseContext);
    }
    if (storyElements) {
      args.push("--story-elements", storyElements);
    }
    if (characterSheets) {
      args.push("--character-sheets", characterSheets);
    }
    if (settingSheets) {
      args.push("--setting-sheets", settingSheets);
    }
    if (previousRecap) {
      args.push("--previous-recap", previousRecap);
    }
    if (previousScene) {
      args.push("--previous-scene", previousScene);
    }
    if (nextSceneDefinition) {
      args.push("--next-scene-definition", nextSceneDefinition);
    }
    if (nextChapterSynopsis) {
      args.push("--next-chapter-synopsis", nextChapterSynopsis);
    }
    if (model) {
      args.push("--model", model);
    }
    if (chapterText) {
      args.push("--chapter-text", chapterText);
    }
    if (priorChaptersSummary) {
      args.push("--prior-chapters-summary", priorChaptersSummary);
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
