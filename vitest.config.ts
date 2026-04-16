import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: [".opencode/plugins/__tests__/**/*.test.ts"],
  },
});
