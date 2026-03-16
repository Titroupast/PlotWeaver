import { expect, test } from "@playwright/test";

test("project -> configure -> run -> review key path", async ({ page }) => {
  await page.goto("/app/projects");
  await expect(page.getByRole("heading", { name: "Projects" })).toBeVisible();

  await page.getByRole("button", { name: "Open" }).first().click();
  await expect(page).toHaveURL(/\/app\/projects\/proj-1$/);

  await page.getByRole("button", { name: "Configure Continuation" }).first().click();
  await expect(page).toHaveURL(/\/configure$/);

  await page.getByLabel("Chapter Goal").fill("Continue the siege chapter with tactical misdirection.");
  await page.getByRole("button", { name: "Create Requirement & Run" }).click();

  await expect(page).toHaveURL(/\/runs\/run-1$/);
  await expect(page.getByRole("heading", { name: "生成过程" })).toBeVisible();

  await page.getByRole("button", { name: "Go To Review" }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByRole("heading", { name: "结果审阅" })).toBeVisible();
  await expect(page.getByText("OUTLINE")).toBeVisible();
  await expect(page.getByText("MEMORY_GATE")).toBeVisible();
});
