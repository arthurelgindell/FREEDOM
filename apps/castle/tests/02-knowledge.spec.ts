import { test, expect } from '@playwright/test';

test.describe('Knowledge Base Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/knowledge');
  });

  test('should load knowledge page with search and ingest tabs', async ({ page }) => {
    // Check page title and navigation
    await expect(page.getByRole('heading', { name: 'Knowledge Base' })).toBeVisible();

    // Check tabs are present
    await expect(page.getByRole('button', { name: /search/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /ingest/i })).toBeVisible();

    // Search tab should be active by default
    await expect(page.locator('text=Knowledge Search')).toBeVisible();
  });

  test('should allow switching between search and ingest tabs', async ({ page }) => {
    // Click on ingest tab
    await page.getByRole('button', { name: /ingest/i }).click();

    // Check ingest form is visible
    await expect(page.locator('text=Ingest Specification')).toBeVisible();
    await expect(page.getByPlaceholder('e.g., React, Python, PostgreSQL')).toBeVisible();

    // Click back to search tab
    await page.getByRole('button', { name: /search/i }).click();

    // Check search form is visible
    await expect(page.locator('text=Knowledge Search')).toBeVisible();
    await expect(page.getByPlaceholder(/enter your search query/i)).toBeVisible();
  });

  test('should perform knowledge base search', async ({ page }) => {
    // Mock successful search response
    await page.route('**/kb/query', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          results: [
            {
              component_name: 'Button',
              technology_name: 'React',
              version: '18.0.0',
              component_type: 'component',
              specification: {
                props: { onClick: 'function', children: 'ReactNode' }
              },
              source_url: 'https://example.com/react-button',
              confidence_score: 0.95,
              similarity_score: 0.87
            }
          ],
          total_results: 1,
          query_embedding_time_ms: 45,
          search_time_ms: 23,
          total_time_ms: 68
        })
      });
    });

    // Fill search form
    await page.getByPlaceholder(/enter your search query/i).fill('React button component');
    await page.getByRole('button', { name: /search/i }).click();

    // Wait for results
    await expect(page.locator('text=Search Results')).toBeVisible();
    await expect(page.locator('text=Button')).toBeVisible();
    await expect(page.locator('text=React')).toBeVisible();
    await expect(page.locator('text=87%')).toBeVisible(); // similarity score
  });

  test('should handle search errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/kb/query', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Service unavailable' })
      });
    });

    // Perform search
    await page.getByPlaceholder(/enter your search query/i).fill('test query');
    await page.getByRole('button', { name: /search/i }).click();

    // Check error is displayed
    await expect(page.locator('text=Search Failed')).toBeVisible();
  });

  test('should allow specification ingestion', async ({ page }) => {
    // Switch to ingest tab
    await page.getByRole('button', { name: /ingest/i }).click();

    // Mock successful ingest response
    await page.route('**/kb/ingest', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          specification_id: 'spec-123',
          message: 'Specification ingested successfully',
          processing_time_ms: 156
        })
      });
    });

    // Fill ingest form
    await page.getByPlaceholder('e.g., React, Python, PostgreSQL').fill('React');
    await page.getByPlaceholder('e.g., 18.2.0, 3.11, 15.0').fill('18.2.0');
    await page.getByPlaceholder('e.g., component, library, framework').fill('component');
    await page.getByPlaceholder('e.g., Button, Chart, DataTable').fill('TestComponent');
    await page.getByPlaceholder('https://...').fill('https://example.com/test');

    const specTextarea = page.locator('textarea[placeholder*="props"]');
    await specTextarea.fill('{"props": {"title": "string", "onClick": "function"}}');

    // Submit form
    await page.getByRole('button', { name: /ingest specification/i }).click();

    // Check success message
    await expect(page.locator('text=Specification Ingested Successfully')).toBeVisible();
    await expect(page.locator('text=spec-123')).toBeVisible();
  });

  test('should validate ingest form fields', async ({ page }) => {
    // Switch to ingest tab
    await page.getByRole('button', { name: /ingest/i }).click();

    // Try to submit empty form
    const submitButton = page.getByRole('button', { name: /ingest specification/i });
    await expect(submitButton).toBeDisabled();

    // Fill required fields one by one and check button state
    await page.getByPlaceholder('e.g., React, Python, PostgreSQL').fill('React');
    await expect(submitButton).toBeDisabled();

    await page.getByPlaceholder('e.g., Button, Chart, DataTable').fill('TestComponent');
    await expect(submitButton).toBeEnabled();
  });

  test('should export search results', async ({ page }) => {
    // Mock successful search
    await page.route('**/kb/query', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          results: [{ component_name: 'Button', technology_name: 'React' }],
          total_results: 1,
          total_time_ms: 68
        })
      });
    });

    // Perform search
    await page.getByPlaceholder(/enter your search query/i).fill('test');
    await page.getByRole('button', { name: /search/i }).click();

    // Wait for results and export button
    await expect(page.locator('text=Search Results')).toBeVisible();

    // Set up download listener
    const downloadPromise = page.waitForEvent('download');

    // Click export button
    await page.getByRole('button', { name: /export results/i }).click();

    // Wait for download
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/knowledge-search-\d+\.json/);
  });

  test('should handle invalid JSON in specification', async ({ page }) => {
    // Switch to ingest tab
    await page.getByRole('button', { name: /ingest/i }).click();

    // Fill form with invalid JSON
    await page.getByPlaceholder('e.g., React, Python, PostgreSQL').fill('React');
    await page.getByPlaceholder('e.g., Button, Chart, DataTable').fill('TestComponent');

    const specTextarea = page.locator('textarea[placeholder*="props"]');
    await specTextarea.fill('invalid json {');

    // Submit form
    await page.getByRole('button', { name: /ingest specification/i }).click();

    // Check for error alert (assuming it shows an alert)
    page.on('dialog', dialog => {
      expect(dialog.message()).toContain('Invalid JSON');
      dialog.accept();
    });
  });

  test('should copy specification to clipboard', async ({ page }) => {
    // Mock successful search with results
    await page.route('**/kb/query', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          results: [
            {
              component_name: 'Button',
              technology_name: 'React',
              specification: { props: { onClick: 'function' } },
              similarity_score: 0.87
            }
          ],
          total_results: 1,
          total_time_ms: 68
        })
      });
    });

    // Grant clipboard permissions
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);

    // Perform search
    await page.getByPlaceholder(/enter your search query/i).fill('button');
    await page.getByRole('button', { name: /search/i }).click();

    // Wait for results and click copy button
    await expect(page.locator('text=Search Results')).toBeVisible();
    await page.locator('button').filter({ hasText: /copy/i }).first().click();

    // Verify clipboard content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toContain('props');
    expect(clipboardText).toContain('onClick');
  });
});