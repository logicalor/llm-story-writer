import { z } from "zod";
import { execFileSync } from "child_process";
import { resolve } from "path";

export default {
  name: "wiki-update",
  description:
    "Create, update, and manage wiki pages. Handles page CRUD, index maintenance, timeline updates, operation logging, and ChromaDB re-embedding.",
  parameters: z.object({
    operation: z
      .enum(["create", "update", "append-timeline", "batch", "log"])
      .describe("Operation to perform"),
    name: z.string().describe("Story name (directory under stories/)"),
    slug: z.string().optional().describe("Page slug (required for create/update)"),
    pageType: z
      .string()
      .optional()
      .describe(
        "Page type: character|location|event|faction|item|plot_thread|world_rule|theme|relationship|timeline_entry|chapter_synopsis (required for create)"
      ),
    pageName: z
      .string()
      .optional()
      .describe("Display name for the page (required for create)"),
    body: z.string().optional().describe("Page body markdown"),
    mergeBody: z
      .string()
      .optional()
      .describe("Content to append to existing body (update only)"),
    confidence: z
      .string()
      .optional()
      .describe("Confidence level: verified|planned|speculative"),
    firstAppearance: z
      .number()
      .optional()
      .describe("Chapter number of first appearance"),
    aliases: z.string().optional().describe("JSON array string of aliases"),
    detailLevels: z
      .string()
      .optional()
      .describe("JSON object string with L1, L2, L3 keys"),
    frontmatter: z
      .string()
      .optional()
      .describe("JSON object of frontmatter fields to merge (update only)"),
    role: z.string().optional().describe("Character role"),
    status: z.string().optional().describe("Character/plot_thread status"),
    region: z.string().optional().describe("Location region"),
    chapter: z.number().optional().describe("Event chapter number"),
    impact: z.string().optional().describe("Event impact description"),
    events: z
      .string()
      .optional()
      .describe("JSON array of timeline events (append-timeline only)"),
    payload: z
      .string()
      .optional()
      .describe("JSON payload for batch operations"),
    message: z.string().optional().describe("Log message (log only)"),
  }),
  execute: async ({
    operation,
    name,
    slug,
    pageType,
    pageName,
    body,
    mergeBody,
    confidence,
    firstAppearance,
    aliases,
    detailLevels,
    frontmatter,
    role,
    status,
    region,
    chapter,
    impact,
    events,
    payload,
    message,
  }: {
    operation: string;
    name: string;
    slug?: string;
    pageType?: string;
    pageName?: string;
    body?: string;
    mergeBody?: string;
    confidence?: string;
    firstAppearance?: number;
    aliases?: string;
    detailLevels?: string;
    frontmatter?: string;
    role?: string;
    status?: string;
    region?: string;
    chapter?: number;
    impact?: string;
    events?: string;
    payload?: string;
    message?: string;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/wiki_update.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (slug) {
      args.push("--slug", slug);
    }
    if (pageType) {
      args.push("--page-type", pageType);
    }
    if (pageName) {
      args.push("--page-name", pageName);
    }
    if (body) {
      args.push("--body", body);
    }
    if (mergeBody) {
      args.push("--merge-body", mergeBody);
    }
    if (confidence) {
      args.push("--confidence", confidence);
    }
    if (firstAppearance !== undefined) {
      args.push("--first-appearance", String(firstAppearance));
    }
    if (aliases) {
      args.push("--aliases", aliases);
    }
    if (detailLevels) {
      args.push("--detail-levels", detailLevels);
    }
    if (frontmatter) {
      args.push("--frontmatter", frontmatter);
    }
    if (role) {
      args.push("--role", role);
    }
    if (status) {
      args.push("--status", status);
    }
    if (region) {
      args.push("--region", region);
    }
    if (chapter !== undefined) {
      args.push("--chapter", String(chapter));
    }
    if (impact) {
      args.push("--impact", impact);
    }
    if (events) {
      args.push("--events", events);
    }
    if (payload) {
      args.push("--payload", payload);
    }
    if (message) {
      args.push("--message", message);
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
      const errorMessage =
        execError.stderr?.trim() || execError.message || "Unknown error";
      return `Error: ${errorMessage}`;
    }
  },
};
