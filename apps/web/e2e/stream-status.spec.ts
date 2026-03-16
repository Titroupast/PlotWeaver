import { expect, test } from "@playwright/test";

test("run page exposes stream status and event timeline", async ({ page }) => {
  await page.goto("/app/projects/proj-1/chapters/chap-1/runs/run-1");
  await expect(page.getByRole("heading", { name: "生成过程" })).toBeVisible();
  await expect(page.getByText("stream:")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Event Timeline" })).toBeVisible();
});
