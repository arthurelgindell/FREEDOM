import { test, expect } from '@playwright/test';

test.describe('Runs Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/runs');
  });

  test('should load runs page with statistics and run list', async ({ page }) => {
    // Check page title
    await expect(page.getByRole('heading', { name: 'Task Runs' })).toBeVisible();

    // Check stats cards
    await expect(page.getByText('Total Runs')).toBeVisible();
    await expect(page.getByText('Running')).toBeVisible();
    await expect(page.getByText('Completed')).toBeVisible();
    await expect(page.getByText('Failed')).toBeVisible();

    // Check control buttons
    await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /new run/i })).toBeVisible();
  });

  test('should display mock runs data', async ({ page }) => {
    // Check that mock runs are displayed
    await expect(page.locator('text=React Component Search')).toBeVisible();
    await expect(page.locator('text=API Integration Query')).toBeVisible();
    await expect(page.locator('text=Database Schema Search')).toBeVisible();

    // Check status badges
    await expect(page.locator('text=Completed')).toBeVisible();
    await expect(page.locator('text=Running')).toBeVisible();
    await expect(page.locator('text=Failed')).toBeVisible();
  });

  test('should open and close new run form', async ({ page }) => {
    // Click new run button
    await page.getByRole('button', { name: /new run/i }).click();

    // Check form is visible
    await expect(page.locator('text=Create New Run')).toBeVisible();
    await expect(page.getByPlaceholder('e.g., React Component Search')).toBeVisible();
    await expect(page.getByPlaceholder('Enter your knowledge base query...')).toBeVisible();

    // Click cancel
    await page.getByRole('button', { name: /cancel/i }).click();

    // Check form is hidden
    await expect(page.locator('text=Create New Run')).not.toBeVisible();
  });

  test('should create a new run', async ({ page }) => {
    // Open new run form
    await page.getByRole('button', { name: /new run/i }).click();

    // Fill form
    await page.getByPlaceholder('e.g., React Component Search').fill('Test Search Run');
    await page.getByPlaceholder('Enter your knowledge base query...').fill('Find React hooks for state management');

    // Submit form
    await page.getByRole('button', { name: /create run/i }).click();

    // Wait for form to close and page to refresh
    await expect(page.locator('text=Create New Run')).not.toBeVisible();

    // The new run should appear in the list (this is mocked behavior)
    // In a real scenario, this would depend on the API response
  });

  test('should validate new run form', async ({ page }) => {
    // Open new run form
    await page.getByRole('button', { name: /new run/i }).click();

    // Check submit button is disabled when form is empty
    const submitButton = page.getByRole('button', { name: /create run/i });
    await expect(submitButton).toBeDisabled();

    // Fill only name
    await page.getByPlaceholder('e.g., React Component Search').fill('Test Run');
    await expect(submitButton).toBeDisabled();

    // Fill both fields
    await page.getByPlaceholder('Enter your knowledge base query...').fill('test query');
    await expect(submitButton).toBeEnabled();

    // Clear name field
    await page.getByPlaceholder('e.g., React Component Search').clear();
    await expect(submitButton).toBeDisabled();
  });

  test('should filter runs by status', async ({ page }) => {
    // Check all runs are visible initially
    await expect(page.locator('text=React Component Search')).toBeVisible();
    await expect(page.locator('text=API Integration Query')).toBeVisible();
    await expect(page.locator('text=Database Schema Search')).toBeVisible();

    // Filter by completed status
    await page.selectOption('select', 'completed');

    // Should only show completed runs
    await expect(page.locator('text=React Component Search')).toBeVisible();
    await expect(page.locator('text=API Integration Query')).not.toBeVisible();

    // Filter by running status
    await page.selectOption('select', 'running');

    // Should only show running runs
    await expect(page.locator('text=API Integration Query')).toBeVisible();
    await expect(page.locator('text=React Component Search')).not.toBeVisible();

    // Reset filter
    await page.selectOption('select', 'all');

    // All runs should be visible again
    await expect(page.locator('text=React Component Search')).toBeVisible();
    await expect(page.locator('text=API Integration Query')).toBeVisible();
  });

  test('should search runs by text', async ({ page }) => {
    // Search for "React"
    await page.getByPlaceholder('Search runs...').fill('React');

    // Should only show React-related runs
    await expect(page.locator('text=React Component Search')).toBeVisible();
    await expect(page.locator('text=API Integration Query')).not.toBeVisible();

    // Search for "API"
    await page.getByPlaceholder('Search runs...').clear();
    await page.getByPlaceholder('Search runs...').fill('API');

    // Should only show API-related runs
    await expect(page.locator('text=API Integration Query')).toBeVisible();
    await expect(page.locator('text=React Component Search')).not.toBeVisible();

    // Clear search
    await page.getByPlaceholder('Search runs...').clear();

    // All runs should be visible again
    await expect(page.locator('text=React Component Search')).toBeVisible();
    await expect(page.locator('text=API Integration Query')).toBeVisible();
  });

  test('should show run details and actions', async ({ page }) => {
    // Check run details are visible
    const reactRun = page.locator('text=React Component Search').locator('..');

    // Check basic info
    await expect(reactRun.locator('text=Created:')).toBeVisible();
    await expect(reactRun.locator('text=Completed:')).toBeVisible();
    await expect(reactRun.locator('text=Duration:')).toBeVisible();
    await expect(reactRun.locator('text=Results:')).toBeVisible();

    // Check action buttons
    await expect(reactRun.getByTitle('View details')).toBeVisible();
    await expect(reactRun.getByTitle('Download results')).toBeVisible();
    await expect(reactRun.getByTitle('Delete run')).toBeVisible();
  });

  test('should show results preview for completed runs', async ({ page }) => {
    // Find completed run
    const reactRun = page.locator('text=React Component Search').locator('..');

    // Check results preview
    await expect(reactRun.locator('text=Results Preview')).toBeVisible();
    await expect(reactRun.locator('text=Chart.js')).toBeVisible();
    await expect(reactRun.locator('text=D3.js')).toBeVisible();
    await expect(reactRun.locator('text=95%')).toBeVisible(); // confidence score
  });

  test('should show error message for failed runs', async ({ page }) => {
    // Find failed run
    const failedRun = page.locator('text=Database Schema Search').locator('..');

    // Check error message
    await expect(failedRun.locator('text=Error:')).toBeVisible();
    await expect(failedRun.locator('text=Connection timeout')).toBeVisible();
  });

  test('should refresh runs data', async ({ page }) => {
    // Click refresh button
    const refreshButton = page.getByRole('button', { name: /refresh/i });
    await refreshButton.click();

    // Check for loading state
    await expect(page.locator('.animate-spin')).toBeVisible();

    // Data should reload (in this case, same mock data)
    await expect(page.locator('text=React Component Search')).toBeVisible();
  });

  test('should show empty state when no runs match filters', async ({ page }) => {
    // Search for something that doesn't exist
    await page.getByPlaceholder('Search runs...').fill('nonexistent search term');

    // Should show empty state
    await expect(page.locator('text=No runs found')).toBeVisible();
    await expect(page.locator('text=Try adjusting your search')).toBeVisible();
  });

  test('should show create first run button when no runs exist', async ({ page }) => {
    // Mock empty runs response
    await page.route('**/runs', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    await page.reload();

    // Should show empty state with create button
    await expect(page.locator('text=No runs found')).toBeVisible();
    await expect(page.getByRole('button', { name: /create first run/i })).toBeVisible();
  });

  test('should handle different run statuses correctly', async ({ page }) => {
    // Check pending status (if any exists in mock data)
    // This would depend on the mock data structure

    // Check running status with ongoing indicator
    const runningRun = page.locator('text=API Integration Query').locator('..');
    await expect(runningRun.locator('text=Running')).toBeVisible();

    // Check completed status with results
    const completedRun = page.locator('text=React Component Search').locator('..');
    await expect(completedRun.locator('text=Completed')).toBeVisible();

    // Check failed status with error
    const failedRun = page.locator('text=Database Schema Search').locator('..');
    await expect(failedRun.locator('text=Failed')).toBeVisible();
  });
});