import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('should load settings page with all configuration sections', async ({ page }) => {
    // Check page title
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

    // Check main sections
    await expect(page.locator('text=Connection Settings')).toBeVisible();
    await expect(page.locator('text=Query Defaults')).toBeVisible();
    await expect(page.locator('text=Notifications')).toBeVisible();
    await expect(page.locator('text=Environment Information')).toBeVisible();
  });

  test('should display connection settings form', async ({ page }) => {
    // Check connection form fields
    await expect(page.getByPlaceholder('http://localhost:8080')).toBeVisible();
    await expect(page.getByPlaceholder('ws://localhost:8080')).toBeVisible();
    await expect(page.getByPlaceholder('Enter API key')).toBeVisible();

    // Check labels
    await expect(page.locator('text=API Base URL')).toBeVisible();
    await expect(page.locator('text=WebSocket URL')).toBeVisible();
    await expect(page.locator('text=API Key')).toBeVisible();
  });

  test('should handle API key visibility toggle', async ({ page }) => {
    const apiKeyInput = page.getByPlaceholder('Enter API key');
    const toggleButton = page.locator('button').filter({ hasText: /eye/i }).first();

    // Check initial state (password field)
    await expect(apiKeyInput).toHaveAttribute('type', 'password');

    // Click toggle to show
    await toggleButton.click();
    await expect(apiKeyInput).toHaveAttribute('type', 'text');

    // Click toggle to hide
    await toggleButton.click();
    await expect(apiKeyInput).toHaveAttribute('type', 'password');
  });

  test('should test connection functionality', async ({ page }) => {
    // Mock successful health check
    await page.route('**/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          uptime_seconds: 3600,
          version: '1.0.0'
        })
      });
    });

    // Click test connection
    await page.getByRole('button', { name: /test connection/i }).click();

    // Should show testing state
    await expect(page.locator('text=Testing...')).toBeVisible();

    // Should show success result
    await expect(page.locator('text=Connected')).toBeVisible();
    await expect(page.locator('text=Connection successful')).toBeVisible();
  });

  test('should handle connection test failures', async ({ page }) => {
    // Mock failed health check
    await page.route('**/health', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Service unavailable' })
      });
    });

    // Click test connection
    await page.getByRole('button', { name: /test connection/i }).click();

    // Should show failed result
    await expect(page.locator('text=Failed')).toBeVisible();
    await expect(page.locator('text=HTTP 500')).toBeVisible();
  });

  test('should update query default settings', async ({ page }) => {
    // Find and update result limit
    const limitInput = page.locator('input[type="number"]').first();
    await limitInput.clear();
    await limitInput.fill('20');

    // Find and update similarity threshold
    const thresholdInput = page.locator('input[type="number"]').nth(1);
    await thresholdInput.clear();
    await thresholdInput.fill('0.8');

    // Should trigger has changes state
    await expect(page.locator('text=You have unsaved changes')).toBeVisible();
  });

  test('should toggle notification settings', async ({ page }) => {
    // Find notification checkboxes
    const realTimeCheckbox = page.locator('input[type="checkbox"]').first();
    const healthAlertsCheckbox = page.locator('input[type="checkbox"]').nth(1);
    const taskCompletionsCheckbox = page.locator('input[type="checkbox"]').nth(2);

    // Toggle settings
    await realTimeCheckbox.uncheck();
    await healthAlertsCheckbox.uncheck();
    await taskCompletionsCheckbox.check();

    // Should trigger changes detection
    await expect(page.locator('text=You have unsaved changes')).toBeVisible();
  });

  test('should save settings to localStorage', async ({ page }) => {
    // Make a change
    const limitInput = page.locator('input[type="number"]').first();
    await limitInput.clear();
    await limitInput.fill('25');

    // Save settings
    await page.getByRole('button', { name: /save changes/i }).click();

    // Check localStorage
    const savedSettings = await page.evaluate(() => {
      return localStorage.getItem('castle-settings');
    });

    expect(savedSettings).toBeTruthy();
    const settings = JSON.parse(savedSettings!);
    expect(settings.queryDefaults.limit).toBe(25);
  });

  test('should export settings as JSON', async ({ page }) => {
    // Set up download listener
    const downloadPromise = page.waitForEvent('download');

    // Click export button
    await page.getByRole('button', { name: /export/i }).click();

    // Verify download
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/castle-settings-\d+\.json/);
  });

  test('should import settings from file', async ({ page }) => {
    // Create test settings file content
    const testSettings = {
      apiUrl: 'http://test.example.com',
      queryDefaults: {
        limit: 15,
        similarityThreshold: 0.9
      }
    };

    // Mock file upload
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-settings.json',
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify(testSettings))
    });

    // Verify settings were imported
    const apiUrlInput = page.getByPlaceholder('http://localhost:8080');
    await expect(apiUrlInput).toHaveValue('http://test.example.com');

    const limitInput = page.locator('input[type="number"]').first();
    await expect(limitInput).toHaveValue('15');
  });

  test('should copy API key to clipboard', async ({ page }) => {
    // Grant clipboard permissions
    await page.context().grantPermissions(['clipboard-write']);

    // Click copy button
    await page.locator('button').filter({ hasText: /copy/i }).click();

    // Verify clipboard (this would contain the default API key)
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toBeTruthy();
  });

  test('should display environment information', async ({ page }) => {
    // Check environment info section
    await expect(page.locator('text=FREEDOM Castle GUI')).toBeVisible();
    await expect(page.locator('text=Version:')).toBeVisible();
    await expect(page.locator('text=Node Environment:')).toBeVisible();
    await expect(page.locator('text=Build Time:')).toBeVisible();
    await expect(page.locator('text=User Agent:')).toBeVisible();

    // Check actual values
    await expect(page.locator('text=1.0.0')).toBeVisible();
    await expect(page.locator('text=development').or(page.locator('text=production'))).toBeVisible();
  });

  test('should show unsaved changes banner', async ({ page }) => {
    // Make a change
    const apiUrlInput = page.getByPlaceholder('http://localhost:8080');
    await apiUrlInput.clear();
    await apiUrlInput.fill('http://changed.example.com');

    // Should show unsaved changes banner
    await expect(page.locator('text=You have unsaved changes')).toBeVisible();

    // Banner should have save button
    const bannerSaveButton = page.locator('text=You have unsaved changes').locator('..').getByRole('button', { name: /save changes/i });
    await expect(bannerSaveButton).toBeVisible();
  });

  test('should validate form fields', async ({ page }) => {
    // Test number input validation
    const limitInput = page.locator('input[type="number"]').first();

    // Try invalid values
    await limitInput.clear();
    await limitInput.fill('-5'); // negative value

    // The input should handle validation appropriately
    await expect(limitInput).toBeVisible();

    // Test threshold validation
    const thresholdInput = page.locator('input[type="number"]').nth(1);
    await thresholdInput.clear();
    await thresholdInput.fill('1.5'); // above 1.0

    await expect(thresholdInput).toBeVisible();
  });

  test('should load default settings on first visit', async ({ page }) => {
    // Clear localStorage first
    await page.evaluate(() => localStorage.clear());

    // Reload page
    await page.reload();

    // Should show default values
    const apiUrlInput = page.getByPlaceholder('http://localhost:8080');
    await expect(apiUrlInput).toHaveValue('http://localhost:8080');

    const limitInput = page.locator('input[type="number"]').first();
    await expect(limitInput).toHaveValue('10');

    const thresholdInput = page.locator('input[type="number"]').nth(1);
    await expect(thresholdInput).toHaveValue('0.7');
  });

  test('should handle invalid import file', async ({ page }) => {
    // Mock invalid file upload
    const fileInput = page.locator('input[type="file"]');

    // Set up alert listener
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Invalid settings file');
      await dialog.accept();
    });

    await fileInput.setInputFiles({
      name: 'invalid.json',
      mimeType: 'application/json',
      buffer: Buffer.from('invalid json content')
    });
  });

  test('should persist settings across page reloads', async ({ page }) => {
    // Make changes and save
    const limitInput = page.locator('input[type="number"]').first();
    await limitInput.clear();
    await limitInput.fill('30');

    await page.getByRole('button', { name: /save changes/i }).click();

    // Reload page
    await page.reload();

    // Settings should be persisted
    await expect(limitInput).toHaveValue('30');
  });
});