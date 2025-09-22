import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test('should load dashboard with health information', async ({ page }) => {
    await page.goto('/');

    // Check page title
    await expect(page).toHaveTitle(/FREEDOM Castle/);

    // Check main heading
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

    // Check navigation is present
    await expect(page.getByRole('navigation')).toBeVisible();

    // Check status cards are present
    await expect(page.getByText('System Uptime')).toBeVisible();
    await expect(page.getByText('Services Online')).toBeVisible();
    await expect(page.getByText('KB Status')).toBeVisible();
    await expect(page.getByText('Last Check')).toBeVisible();
  });

  test('should display system status information', async ({ page }) => {
    await page.goto('/');

    // Wait for health check to complete
    await page.waitForSelector('[data-testid="system-status"]', { timeout: 10000 });

    // Check system status card
    const systemCard = page.locator('text=System Status').locator('..');
    await expect(systemCard).toBeVisible();

    // Check services card
    const servicesCard = page.locator('text=Services').locator('..');
    await expect(servicesCard).toBeVisible();
  });

  test('should have working refresh button', async ({ page }) => {
    await page.goto('/');

    // Find and click refresh button
    const refreshButton = page.getByRole('button', { name: /refresh/i });
    await expect(refreshButton).toBeVisible();
    await refreshButton.click();

    // Check for loading state (spinning icon)
    await expect(page.locator('.animate-spin')).toBeVisible();
  });

  test('should have functional quick action buttons', async ({ page }) => {
    await page.goto('/');

    // Check quick actions section
    await expect(page.getByText('Quick Actions')).toBeVisible();

    // Test navigation buttons
    const viewRunsButton = page.getByRole('link', { name: /view runs/i });
    await expect(viewRunsButton).toBeVisible();
    await expect(viewRunsButton).toHaveAttribute('href', '/runs');

    const searchKBButton = page.getByRole('link', { name: /search kb/i });
    await expect(searchKBButton).toBeVisible();
    await expect(searchKBButton).toHaveAttribute('href', '/knowledge');

    const serviceHealthButton = page.getByRole('link', { name: /service health/i });
    await expect(serviceHealthButton).toBeVisible();
    await expect(serviceHealthButton).toHaveAttribute('href', '/services');

    const settingsButton = page.getByRole('link', { name: /settings/i });
    await expect(settingsButton).toBeVisible();
    await expect(settingsButton).toHaveAttribute('href', '/settings');
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Intercept health check API and return error
    await page.route('**/health', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Service unavailable' })
      });
    });

    await page.goto('/');

    // Should show error state in dashboard
    await expect(page.getByText(/unable to connect/i)).toBeVisible();
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Check mobile navigation is visible
    await expect(page.getByRole('button', { name: /menu/i })).toBeVisible();

    // Check content is still visible
    await expect(page.getByText('Dashboard')).toBeVisible();

    // Check cards stack vertically on mobile
    const cards = page.locator('[class*="grid"]').first();
    await expect(cards).toBeVisible();
  });
});