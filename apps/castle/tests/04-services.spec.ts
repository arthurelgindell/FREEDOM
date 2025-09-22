import { test, expect } from '@playwright/test';

test.describe('Services Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/services');
  });

  test('should load services page with health monitoring', async ({ page }) => {
    // Check page title
    await expect(page.getByRole('heading', { name: 'Service Health' })).toBeVisible();

    // Check stats cards
    await expect(page.getByText('Services Online')).toBeVisible();
    await expect(page.getByText('Avg Response')).toBeVisible();
    await expect(page.getByText('Total Requests')).toBeVisible();
    await expect(page.getByText('Last Update')).toBeVisible();

    // Check refresh button
    await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
  });

  test('should display service cards with health information', async ({ page }) => {
    // Check main services are displayed
    await expect(page.locator('text=API Gateway')).toBeVisible();
    await expect(page.locator('text=Knowledge Base Service')).toBeVisible();
    await expect(page.locator('text=PostgreSQL Database')).toBeVisible();
    await expect(page.locator('text=MLX Server')).toBeVisible();

    // Check service descriptions
    await expect(page.locator('text=Main API gateway handling all incoming requests')).toBeVisible();
    await expect(page.locator('text=Vector database and knowledge processing service')).toBeVisible();
  });

  test('should show service status badges', async ({ page }) => {
    // Mock health response
    await page.route('**/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          uptime_seconds: 3600,
          version: '1.0.0',
          kb_service_status: 'healthy',
          kb_service_response_time_ms: 45
        })
      });
    });

    await page.reload();

    // Check status badges
    await expect(page.locator('text=Healthy').first()).toBeVisible();
  });

  test('should display service metrics and resource usage', async ({ page }) => {
    // Check resource usage sections
    await expect(page.locator('text=Resource Usage')).toBeVisible();
    await expect(page.locator('text=CPU:')).toBeVisible();
    await expect(page.locator('text=Memory:')).toBeVisible();

    // Check activity sections
    await expect(page.locator('text=Activity')).toBeVisible();
    await expect(page.locator('text=Connections:')).toBeVisible();
    await expect(page.locator('text=Requests:')).toBeVisible();
    await expect(page.locator('text=Errors:')).toBeVisible();
  });

  test('should show service endpoints and versions', async ({ page }) => {
    // Check endpoint information
    await expect(page.locator('text=localhost:8080')).toBeVisible();
    await expect(page.locator('text=kb-service:8000')).toBeVisible();
    await expect(page.locator('text=postgres:5432')).toBeVisible();

    // Check version information
    await expect(page.locator('text=Version:')).toBeVisible();
  });

  test('should display service action buttons', async ({ page }) => {
    // Check action buttons for each service
    const serviceCards = page.locator('[class*="grid"] > div').filter({ hasText: 'API Gateway' }).first();

    await expect(serviceCards.getByRole('button', { name: /view logs/i })).toBeVisible();
    await expect(serviceCards.getByRole('button', { name: /metrics/i })).toBeVisible();
    await expect(serviceCards.getByRole('button', { name: /config/i })).toBeVisible();
  });

  test('should show response time information', async ({ page }) => {
    // Mock health response with timing data
    await page.route('**/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          uptime_seconds: 3600,
          version: '1.0.0',
          kb_service_status: 'healthy',
          kb_service_response_time_ms: 45
        })
      });
    });

    await page.reload();

    // Check response time is displayed
    await expect(page.locator('text=Response Time:')).toBeVisible();
    await expect(page.locator('text=45ms')).toBeVisible();
  });

  test('should handle service errors gracefully', async ({ page }) => {
    // Mock health API error
    await page.route('**/health', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Service unavailable' })
      });
    });

    await page.reload();

    // Should show error states
    await expect(page.locator('text=Service Alert')).toBeVisible();
    await expect(page.locator('text=Unable to retrieve health information')).toBeVisible();
  });

  test('should display raw metrics data', async ({ page }) => {
    // Mock metrics response
    await page.route('**/metrics', route => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: `# HELP gateway_requests_total Total number of requests processed
gateway_requests_total{method="GET",endpoint="/health",status="200"} 42
# HELP gateway_request_duration_seconds Request duration in seconds
gateway_request_duration_seconds_bucket{method="GET",endpoint="/health",le="0.1"} 42`
      });
    });

    await page.reload();

    // Check raw metrics section
    await expect(page.locator('text=Raw Metrics Data')).toBeVisible();
    await expect(page.locator('text=Prometheus metrics from the API Gateway')).toBeVisible();

    // Check metrics content
    await expect(page.locator('text=gateway_requests_total')).toBeVisible();
  });

  test('should show uptime information', async ({ page }) => {
    // Mock health response with uptime
    await page.route('**/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          uptime_seconds: 7265, // ~2 hours
          version: '1.0.0',
          kb_service_status: 'healthy'
        })
      });
    });

    await page.reload();

    // Check uptime display
    await expect(page.locator('text=Uptime:')).toBeVisible();
    await expect(page.locator('text=2h 1m')).toBeVisible();
  });

  test('should refresh service health data', async ({ page }) => {
    // Click refresh button
    const refreshButton = page.getByRole('button', { name: /refresh/i });
    await refreshButton.click();

    // Check for loading state
    await expect(page.locator('.animate-spin')).toBeVisible();
  });

  test('should show degraded status when services have issues', async ({ page }) => {
    // Mock degraded health response
    await page.route('**/health', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'degraded',
          timestamp: new Date().toISOString(),
          uptime_seconds: 3600,
          version: '1.0.0',
          kb_service_status: 'degraded',
          kb_service_response_time_ms: 1500
        })
      });
    });

    await page.reload();

    // Should show degraded status
    await expect(page.locator('text=Degraded')).toBeVisible();
    await expect(page.locator('text=Service Alert')).toBeVisible();
  });

  test('should display service connection counts', async ({ page }) => {
    // Check connection information is displayed
    await expect(page.locator('text=Connections:')).toBeVisible();

    // Should show actual connection numbers from mock data
    await expect(page.locator('text=12').or(page.locator('text=5')).or(page.locator('text=15'))).toBeVisible();
  });

  test('should show error counts for services', async ({ page }) => {
    // Check error information
    await expect(page.locator('text=Errors:')).toBeVisible();

    // Error counts should be color-coded (red for > 0, green for 0)
    const errorElements = page.locator('text=Errors:').locator('..').locator('span').last();
    await expect(errorElements).toBeVisible();
  });

  test('should handle unknown service states', async ({ page }) => {
    // MLX Server should show unknown status by default
    const mlxCard = page.locator('text=MLX Server').locator('..');
    await expect(mlxCard.locator('text=Unknown')).toBeVisible();
  });

  test('should display progress bars for resource usage', async ({ page }) => {
    // Check for resource usage progress bars
    const progressBars = page.locator('div[style*="width:"]');
    await expect(progressBars.first()).toBeVisible();

    // Should have progress bars for CPU and memory usage
    await expect(page.locator('text=CPU:').locator('..').locator('div[style*="width:"]')).toBeVisible();
    await expect(page.locator('text=Memory:').locator('..').locator('div[style*="width:"]')).toBeVisible();
  });
});