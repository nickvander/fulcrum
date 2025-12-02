import { test, expect } from '@playwright/test';

test.describe('User Management', () => {
    test('should allow admin to create and delete a user', async ({ page }) => {
        const timestamp = new Date().getTime();
        const newUserEmail = `e2e-test-${timestamp}@example.com`;

        await page.goto('/users');

        // Create User
        await page.getByRole('button', { name: 'New User' }).click();
        await expect(page.getByRole('dialog')).toBeVisible();
        await page.getByLabel('Email').fill(newUserEmail);
        await page.getByLabel('Password', { exact: true }).fill('TestPass123!');
        await page.getByLabel('Confirm Password').fill('TestPass123!');
        await page.getByLabel('First Name').fill('E2E');
        await page.getByLabel('Last Name').fill('TestUser');
        await page.getByRole('button', { name: 'Create User' }).click();

        // Verify User Created
        await expect(page.getByText('User created successfully')).toBeVisible();
        // Reload page to verify persistence
        await page.reload();
        // Search for the new user to ensure they are visible
        await page.getByLabel('Search').fill(newUserEmail);
        await page.getByLabel('Search').press('Enter');
        // Wait for table to update (simple wait for now, or wait for response)
        await page.waitForResponse(async response => {
            if (!response.url().includes('/users') || !response.url().includes('search=')) return false;
            if (response.status() !== 200) return false;
            const body = await response.json();
            return Array.isArray(body) && body.some((u: any) => u.email === newUserEmail);
        });

        // Wait for loading to finish (progress bar hidden)
        await expect(page.locator('mat-progress-bar')).not.toBeVisible();

        await expect(page.locator('mat-row').first()).toBeVisible();
        await expect(page.locator('mat-table')).toContainText(newUserEmail, { timeout: 15000 });
        await expect(page.locator('mat-row')).toBeVisible();

        // Delete User
        // Find the row with the email and click delete
        // This might need adjustment based on exact table structure
        // This might need adjustment based on exact table structure
        const userRow = page.locator('mat-row', { hasText: newUserEmail });
        await userRow.getByRole('button', { name: 'Permanently delete user' }).click();

        // Confirm deletion in dialog
        await expect(page.getByRole('dialog')).toBeVisible();
        await page.getByRole('button', { name: 'Delete Permanently' }).click();

        // Verify User Deleted
        // Verify User Deleted
        // Wait for table to update
        await page.waitForResponse(response => response.url().includes('/users') && response.status() === 200);
        await expect(page.locator('mat-table')).not.toContainText(newUserEmail);
    });
});
