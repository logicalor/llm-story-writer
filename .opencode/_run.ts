import { spawnSync } from "child_process";
import { resolve } from "path";

/** Default timeout for tool execution (5 minutes). */
const TOOL_TIMEOUT_MS = 5 * 60 * 1000;

/**
 * Run a Python tool script and return its output.
 *
 * Captures both stdout and stderr. On success, any stderr content
 * (e.g. fuzzy story name warnings) is prepended to the stdout result
 * so the agent can see it. On failure, both streams are joined so
 * structured JSON errors printed to stdout are not silently discarded
 * when stderr happens to be empty.
 *
 * If the tool times out, returns a message telling the agent to retry
 * (savepoints allow resuming from where the tool left off).
 */
export function runTool(
  scriptPath: string,
  args: string[],
  options?: { cwd?: string; timeoutMs?: number }
): string {
  // __dirname is .opencode/, so project root is one level up.
  const cwd = options?.cwd || resolve(__dirname, "..");
  const timeout = options?.timeoutMs || TOOL_TIMEOUT_MS;

  const result = spawnSync("python3", [scriptPath, ...args], {
    cwd,
    encoding: "utf-8",
    stdio: ["pipe", "pipe", "pipe"],
    timeout,
  });

  // Handle timeout — tell agent to retry (savepoints enable resumption)
  if (result.error && (result.error as NodeJS.ErrnoException).code === "ETIMEDOUT") {
    return (
      "⚠ Tool execution timed out. The operation may still be in progress — " +
      "savepoints are created after each step, so retrying the same operation " +
      "will resume from where it left off. Call the same tool again with the " +
      "same parameters to continue."
    );
  }

  const stdout = (result.stdout || "").trim();
  const stderr = (result.stderr || "").trim();

  if (result.status !== 0) {
    // Surface BOTH streams — Python tools often print structured JSON errors
    // to stdout (e.g. `{"status":"error","message":"..."}`) while stderr may
    // be empty, so falling back to stderr alone would silently discard the
    // real error payload.
    const parts = [stderr, stdout].filter(Boolean);
    const detail =
      parts.length > 0
        ? parts.join("\n")
        : result.error?.message || "Unknown error";
    return `Error: ${detail}`;
  }

  // Surface stderr warnings (e.g. fuzzy story name matches) to the agent
  if (stderr) {
    return `⚠ Warning: ${stderr}\n\n${stdout}`;
  }
  return stdout;
}
