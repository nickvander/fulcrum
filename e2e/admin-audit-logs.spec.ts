import { test, expect } from '@playwright/test';

test.describe('Admin Audit Logs', () => {
    test('should allow admin to navigate to audit logs and see entries', async ({ page }) => {
        await page.goto('/products');

        // Open the sidenav if it's closed (responsive design) or just find the link
        // Assuming desktop view for now based on standard E2E setup

        await page.getByRole('link', { name: 'Audit Logs' }).click();

        await expect(page).toHaveURL('/admin/audit-logs');
        await expect(page.getByRole('heading', { name: 'Audit Logs' })).toBeVisible();

        // Check if the table is visible
        await expect(page.locator('table')).toBeVisible();

        // Check for column headers
        await expect(page.getByRole('columnheader', { name: 'Action' })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'User' })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'Date' })).toBeVisible();
    });

    test('should allow filtering audit logs', async ({ page }) => {
        await page.goto('/admin/audit-logs');

        // Filter by Action
        await page.getByLabel('Action').fill('LOGIN');
        const responsePromise = page.waitForResponse(response => response.url().includes('/audit-logs') && response.status() === 200);
        await page.getByRole('button', { name: 'Filter' }).click();
        await responsePromise;

        // Verify rows are filtered (this depends on data existing, so we keep it loose for now)
        // We mainly want to ensure the filter interaction doesn't crash and triggers a reload
        await expect(page.locator('table')).toBeVisible();
    });
});
