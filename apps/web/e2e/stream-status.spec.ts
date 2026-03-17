import { expect, test } from "@playwright/test";

test("run page exposes stream status and event timeline", async ({ page }) => {
  await page.goto("/app/projects");
  await expect(page.getByRole("heading", { name: "项目管理" })).toBeVisible();

  const firstOpen = page.getByRole("button", { name: "进入项目" }).first();
  await expect(firstOpen).toBeVisible();
  await firstOpen.click();

  await page.getByRole("button", { name: "进入续写配置" }).first().click();
  await page.getByLabel("章节目标").fill("流状态可视化测试");
  await page.getByRole("button", { name: "创建需求并进入执行" }).click();

  await expect(page.getByRole("heading", { name: "生成过程" })).toBeVisible();
  await expect(page.getByText("流状态:")).toBeVisible();
  await expect(page.getByRole("heading", { name: "事件时间线" })).toBeVisible();
});