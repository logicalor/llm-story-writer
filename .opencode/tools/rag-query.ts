import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Index and query story content via ChromaDB semantic search. " +
    "Use 'index' to embed a piece of content (outline, chapter, character sheet, setting sheet, wiki page, recap) " +
    "into the story's ChromaDB collection. Use 'query' to retrieve relevant chunks by semantic similarity.",
  args: {
    operation: z
      .enum(["index", "query"])
      .describe("Operation to perform: 'index' to embed content, 'query' to search"),
    name: z.string().describe("Story name (directory under stories/)"),
    docId: z
      .string()
      .optional()
      .describe(
        "Stable document ID for indexing (e.g. 'outline', 'chapter-1', 'character-elena'). Required for index."
      ),
    content: z
      .string()
      .optional()
      .describe("Text content to embed. Required for index."),
    contentType: z
      .enum(["outline", "chapter", "character", "setting", "wiki", "recap", "raw-chapter"])
      .optional()
      .describe("Content type tag. Defaults to 'outline' for index; filters results for query."),
    chapterNum: z
      .number()
      .optional()
      .describe("Chapter number (optional, stored as metadata for chapter content)"),
    query: z
      .string()
      .optional()
      .describe("Search query text. Required for query."),
    nResults: z
      .number()
      .optional()
      .describe("Number of results to return (default: 10)"),
  },
  execute: async ({
    operation,
    name,
    docId,
    content,
    contentType,
    chapterNum,
    query,
    nResults,
  }: {
    operation: string;
    name: string;
    docId?: string;
    content?: string;
    contentType?: string;
    chapterNum?: number;
    query?: string;
    nResults?: number;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/rag_query.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (docId) {
      args.push("--doc-id", docId);
    }
    if (content !== undefined) {
      args.push("--content", content);
    }
    if (contentType) {
      args.push("--content-type", contentType);
    }
    if (chapterNum !== undefined) {
      args.push("--chapter-num", String(chapterNum));
    }
    if (query) {
      args.push("--query", query);
    }
    if (nResults !== undefined) {
      args.push("--n-results", String(nResults));
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
