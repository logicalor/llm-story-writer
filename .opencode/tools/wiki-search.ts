import { tool } from "@opencode-ai/plugin";
const z = tool.schema;
import { execFileSync } from "child_process";
import { resolve } from "path";

export default tool({
  description:
    "Search wiki pages via ChromaDB: semantic search by query text, or metadata-filtered query by JSON where clause. Read-only — does not create collections.",
  args: {
    operation: z
      .enum(["semantic", "metadata"])
      .describe("Operation to perform"),
    name: z.string().describe("Story name (directory under stories/)"),
    query: z
      .string()
      .optional()
      .describe("Search query text (required for semantic)"),
    where: z
      .string()
      .optional()
      .describe("JSON metadata filter string (required for metadata)"),
    nResults: z
      .number()
      .optional()
      .describe("Number of results to return (default: 10)"),
  },
  execute: async ({
    operation,
    name,
    query,
    where,
    nResults,
  }: {
    operation: string;
    name: string;
    query?: string;
    where?: string;
    nResults?: number;
  }) => {
    const projectRoot = resolve(__dirname, "../..");
    const args = [
      "src/tools/wiki_search.py",
      "--operation",
      operation,
      "--name",
      name,
    ];

    if (query) {
      args.push("--query", query);
    }
    if (where) {
      args.push("--where", where);
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
      const execError = error as {
        stdout?: string;
        stderr?: string;
        message?: string;
      };
      const parts = [
        execError.stderr?.trim(),
        execError.stdout?.trim(),
      ].filter(Boolean) as string[];
      const errorMessage =
        parts.length > 0
          ? parts.join("\n")
          : execError.message || "Unknown error";
      return `Error: ${errorMessage}`;
    }
  },
});
