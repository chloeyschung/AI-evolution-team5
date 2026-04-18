import { expect, test } from "@playwright/test";

test("uses canonical Quiet Momentum tokens on the app shell", async ({ page }) => {
  await page.goto("/dashboard");

  const primary = await page.locator(":root").evaluate((el) => {
    return getComputedStyle(el).getPropertyValue("--color-primary").trim();
  });
  const gold = await page.locator(":root").evaluate((el) => {
    return getComputedStyle(el).getPropertyValue("--gold").trim();
  });

  expect(primary).toBe("#2D72D2");
  expect(gold).not.toBe("#b98b24");
});

test("rail and top bar render as one low-chrome family", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("briefly_access_token", "e2e-shell-access-token");
    localStorage.setItem(
      "briefly_auth_state",
      JSON.stringify({
        isAuthenticated: true,
        user: { id: 1, email: "shell@briefly.local", display_name: "Shell Test" },
      }),
    );
  });

  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/api/v1/auth/status")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          is_authenticated: true,
          user_id: 1,
          email: "shell@briefly.local",
        }),
      });
      return;
    }

    if (url.includes("/api/v1/content/pending") || url.includes("/api/v1/search") || url.includes("/api/v1/platforms")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });

  await page.goto("/inbox");
  const rail = page.getByTestId("nav-rail");
  const topBar = page.getByTestId("top-bar");

  await expect(rail).toBeVisible();
  await expect(topBar).toBeVisible();

  const [railBorderWidth, railBorderStyle, railBorderColor, railBackgroundImage] = await rail.evaluate((el) => {
    const styles = getComputedStyle(el);
    return [
      styles.borderRightWidth,
      styles.borderRightStyle,
      styles.borderRightColor,
      styles.backgroundImage,
    ];
  });
  const [topBarBorderWidth, topBarBorderStyle, topBarBorderColor, topBarBackgroundImage] = await topBar.evaluate((el) => {
    const styles = getComputedStyle(el);
    return [
      styles.borderBottomWidth,
      styles.borderBottomStyle,
      styles.borderBottomColor,
      styles.backgroundImage,
    ];
  });

  expect(railBorderWidth).toBe("1px");
  expect(topBarBorderWidth).toBe("1px");
  expect(railBorderStyle).toBe("solid");
  expect(topBarBorderStyle).toBe("solid");
  expect(railBorderColor).toBe(topBarBorderColor);
  expect(railBackgroundImage).toContain("linear-gradient");
  expect(topBarBackgroundImage).toContain("linear-gradient");
});
