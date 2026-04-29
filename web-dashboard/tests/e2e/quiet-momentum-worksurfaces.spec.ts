import { expect, test } from "@playwright/test";

const mockRows = [
  {
    id: 101,
    platform: "YouTube",
    content_type: "video",
    url: "https://example.com/content/101",
    title: "Operational Queue Planning",
    author: "Briefly Ops",
    summary: "A practical breakdown of triage workflow.",
    status: "inbox",
    created_at: "2026-04-10T10:00:00Z",
    updated_at: null,
  },
];
const mockDetail = {
  ...mockRows[0],
  updated_at: "2026-04-11T09:30:00Z",
};

async function primeAuthenticatedSession(page: Parameters<typeof test>[0]["page"]) {
  await page.addInitScript(() => {
    localStorage.setItem("briefly_access_token", "e2e-worksurfaces-access-token");
    localStorage.setItem(
      "briefly_auth_state",
      JSON.stringify({
        isAuthenticated: true,
        user: { id: 1, email: "worksurfaces@briefly.local", display_name: "Worksurfaces Test" },
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
          email: "worksurfaces@briefly.local",
        }),
      });
      return;
    }

    if (/\/api\/v1\/content\/\d+/.test(url)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockDetail),
      });
      return;
    }

    if (url.includes("/api/v1/content")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockRows),
      });
      return;
    }

    if (url.includes("/api/v1/platforms")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ platform: "YouTube", count: 1 }]),
      });
      return;
    }

    if (url.includes("/api/v1/search")) {
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
}

test("dashboard exposes one dominant hero plane and one primary work lane", async ({ page }) => {
  await primeAuthenticatedSession(page);

  await page.goto("/dashboard");
  const hero = page.getByTestId("dashboard-hero-plane");
  const workLane = page.getByTestId("dashboard-work-lane");

  await expect(hero).toBeVisible();
  await expect(workLane).toBeVisible();
  await expect(page.locator('[data-testid="dashboard-hero-plane"]')).toHaveCount(1);
  await expect(page.locator('[data-testid="dashboard-work-lane"]')).toHaveCount(1);

  const heroRadius = await hero.evaluate((el) => getComputedStyle(el).borderRadius);
  expect(heroRadius).toContain("16px");

  const heroShadow = await hero.evaluate((el) => getComputedStyle(el).boxShadow);
  const workLaneBackground = await workLane.evaluate((el) => getComputedStyle(el).backgroundColor);

  expect(heroShadow).not.toBe("none");
  expect(workLaneBackground).not.toBe("rgba(0, 0, 0, 0)");
});

test("inbox and archive prioritize operational copy over marketing slogans", async ({ page }) => {
  await primeAuthenticatedSession(page);

  await page.goto("/inbox");
  await expect(page.getByText("Items requiring action")).toBeVisible();
  await expect(page.getByText(/turn "later" into "learned"/i)).toHaveCount(0);

  await page.goto("/archive");
  await expect(page.getByText("Completed and deferred items")).toBeVisible();
});

test("content table rows use subtle hover emphasis", async ({ page }) => {
  await primeAuthenticatedSession(page);

  await page.goto("/inbox");
  const firstRow = page.getByTestId("content-table-row").first();
  const before = await firstRow.evaluate((el) => getComputedStyle(el).backgroundColor);
  await firstRow.hover();
  const after = await firstRow.evaluate((el) => getComputedStyle(el).backgroundColor);

  expect(after).not.toBe(before);
  expect(after).not.toBe("rgba(0, 0, 0, 0)");
});

test("drawer progression motion contract uses non-zero transition timing", async ({ page }) => {
  await primeAuthenticatedSession(page);

  await page.goto("/inbox");
  await page.getByTestId("content-table-row").first().locator("button").first().click();

  const drawer = page.locator("aside[aria-label]").first();
  await expect(drawer).toBeVisible();

  const transitionDuration = await drawer.evaluate((el) => getComputedStyle(el).transitionDuration);
  expect(transitionDuration).not.toBe("0s");
});

test("quiet momentum motion categories expose non-zero timing tokens", async ({ page }) => {
  await primeAuthenticatedSession(page);

  await page.goto("/inbox");
  const root = page.locator(":root");

  const arrivalDuration = await root.evaluate((el) =>
    getComputedStyle(el).getPropertyValue("--motion-arrival-duration").trim(),
  );
  const progressionDuration = await root.evaluate((el) =>
    getComputedStyle(el).getPropertyValue("--motion-progression-duration").trim(),
  );
  const affordanceDuration = await root.evaluate((el) =>
    getComputedStyle(el).getPropertyValue("--motion-affordance-duration").trim(),
  );

  expect(arrivalDuration).not.toBe("");
  expect(arrivalDuration).not.toBe("0ms");
  expect(progressionDuration).not.toBe("");
  expect(progressionDuration).not.toBe("0ms");
  expect(affordanceDuration).not.toBe("");
  expect(affordanceDuration).not.toBe("0ms");
});

test("reduced motion compresses quiet momentum timing tokens safely", async ({ page }) => {
  await primeAuthenticatedSession(page);
  await page.emulateMedia({ reducedMotion: "reduce" });

  await page.goto("/inbox");
  const root = page.locator(":root");

  const arrivalDuration = await root.evaluate((el) =>
    getComputedStyle(el).getPropertyValue("--motion-arrival-duration").trim(),
  );
  const progressionDuration = await root.evaluate((el) =>
    getComputedStyle(el).getPropertyValue("--motion-progression-duration").trim(),
  );
  const affordanceDuration = await root.evaluate((el) =>
    getComputedStyle(el).getPropertyValue("--motion-affordance-duration").trim(),
  );

  expect(arrivalDuration).toBe("1ms");
  expect(progressionDuration).toBe("1ms");
  expect(affordanceDuration).toBe("1ms");

  await page.getByTestId("content-table-row").first().locator("button").first().click();
  const drawer = page.locator("aside[aria-label]").first();
  await expect(drawer).toBeVisible();

  const transitionDuration = await drawer.evaluate((el) => getComputedStyle(el).transitionDuration);
  expect(transitionDuration).toBe("0.001s");
});
