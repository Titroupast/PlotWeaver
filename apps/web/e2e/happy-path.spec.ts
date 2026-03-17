import { expect, test } from "@playwright/test";

test("project -> create -> configure -> run -> review key path", async ({ page }) => {
  await page.goto("/app/projects");
  await expect(page.getByRole("heading", { name: "项目管理" })).toBeVisible();

  await page.getByLabel("项目标题").fill("E2E Project");
  await page.getByLabel("项目简介").fill("Created by playwright");
  await page.getByRole("button", { name: "创建项目" }).click();

  const card = page.getByRole("article").filter({ hasText: "E2E Project" }).first();
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "进入项目" }).click();

  await expect(page).toHaveURL(/\/app\/projects\/[^/]+$/);

  await page.getByRole("button", { name: "进入续写配置" }).first().click();
  await expect(page).toHaveURL(/\/configure$/);

  await page.getByLabel("章节目标").fill("推进主线并暴露新线索");
  await page.getByRole("button", { name: "创建需求并进入执行" }).click();

  await expect(page).toHaveURL(/\/runs\/[^/]+$/);
  await expect(page.getByRole("heading", { name: "生成过程" })).toBeVisible();

  const nextBtn = page.getByRole("button", { name: /开始第一步|继续下一步/ });
  for (let i = 0; i < 4; i += 1) {
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
    }
  }

  await page.getByRole("button", { name: "查看审阅页" }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByRole("heading", { name: "结果审阅" })).toBeVisible();
});