import { expect, test } from "@playwright/test";

test("project -> create -> configure -> run -> review key path", async ({ page }) => {
  await page.goto("/app/projects");
  await expect(page.getByRole("heading", { name: "Projects 项目" })).toBeVisible();

  await page.getByLabel("Project Title").fill("E2E Project");
  await page.getByLabel("Description").fill("Created by playwright");
  await page.getByRole("button", { name: "Create Project" }).click();

  const card = page.getByRole("article").filter({ hasText: "E2E Project" }).first();
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Open" }).click();

  await expect(page).toHaveURL(/\/app\/projects\/proj-/);

  await page.getByRole("button", { name: "Configure Continuation" }).first().click();
  await expect(page).toHaveURL(/\/configure$/);

  await page.getByLabel("Chapter Goal").fill("Continue the siege chapter with tactical misdirection.");
  await page.getByRole("button", { name: "Create Requirement & Run" }).click();

  await expect(page).toHaveURL(/\/runs\/run-1$/);
  await expect(page.getByRole("heading", { name: "生成过程" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Latest Chapter Content 最新正文" })).toBeVisible();

  await page.getByRole("button", { name: "Go To Review" }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByRole("heading", { name: "结果审阅" })).toBeVisible();
  await expect(page.getByText("OUTLINE")).toBeVisible();
  await expect(page.getByText("MEMORY_GATE")).toBeVisible();
});