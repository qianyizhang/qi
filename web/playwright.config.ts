import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:18765", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { viewport: { width: 1200, height: 900 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command:
      "npm run build && ../.venv/bin/python e2e/prepare.py && QI_BENCHMARK_ROOTS=.test-artifacts/benchmarks QI_BENCHMARK_STATE=.test-artifacts/benchmark-state QI_COLLECTION_PATHS=.test-artifacts/collections/review.sqlite QI_WORKSPACE=.test-artifacts QI_EXPERIMENT_ROOTS=.test-artifacts/runs QI_LAB_STATE=.test-artifacts/jobs ../.venv/bin/uvicorn qi.api:create_app --factory --host 127.0.0.1 --port 18765",
    url: "http://127.0.0.1:18765",
    reuseExistingServer: false,
  },
});
