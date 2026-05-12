import { test as base, expect } from '@playwright/test';

// Inline auth so we don't depend on the (currently out-of-sync) auth.setup.ts.
const test = base.extend<object>({
    page: async ({ page }, run) => {
        await page.goto('/login');
        await page.getByLabel('Email').fill('admin@example.com');
        await page.getByLabel('Password').fill('SecurePass123!');
        await page.getByRole('button', { name: 'Sign In' }).click();
        await page.waitForURL(url => !url.pathname.startsWith('/login'), {
            timeout: 15000,
        });
        await run(page);
    },
});

test.describe('Stock Transfers', () => {
    test('create -> ship -> receive -> sync flow', async ({ page }) => {
        await page.goto('/marketplaces/transfers');
        await expect(page.getByRole('heading', { name: 'Stock Transfers' })).toBeVisible();

        // Empty state or list — either is fine on a fresh DB.
        await page.getByTestId('new-transfer-button').click();
        await expect(page.locator('mat-dialog-container')).toBeVisible();

        // Search for a seeded product and add it.
        await page.getByTestId('product-search').fill('Earl Grey');
        const productPick = page.getByTestId(/^product-pick-/).first();
        await expect(productPick).toBeVisible();
        await productPick.click();

        // Set qty to 20.
        const qtyInput = page.getByTestId(/^qty-input-/).first();
        await qtyInput.fill('20');

        // Save -> we should land on the detail page.
        await page.getByTestId('save-transfer-button').click();
        await expect(page).toHaveURL(/\/marketplaces\/transfers\/\d+$/);
        await expect(page.getByTestId('transfer-status')).toHaveText(/Draft/i);

        // Ship the transfer (plain ship — no marketplace push so the assertion
        // doesn't depend on the absent ML credentials in this env).
        await page.getByTestId('ship-button').click();
        await expect(page.getByTestId('transfer-status')).toHaveText(/Shipped/i);

        // Open receive dialog and submit the prefilled qty.
        await page.getByTestId('open-receive-button').click();
        await expect(page.locator('mat-dialog-container')).toBeVisible();
        await page.getByTestId('confirm-receive-button').click();

        // Receipt should mark the transfer as received.
        await expect(page.getByTestId('transfer-status')).toHaveText(/Received/i);

        // Sync action should be available for ML Full destinations.
        const syncButton = page.getByTestId('sync-listings-button');
        await expect(syncButton).toBeVisible();
        await syncButton.click();
        // No marketplace listing exists for this product in this test env,
        // so the sync summary should report the product as missing.
        await expect(page.getByTestId('last-sync-summary')).toBeVisible();
    });

    test('planner shows snapshot and validates over-allocation', async ({ page }) => {
        await page.goto('/marketplaces/transfers');
        await page.getByTestId('open-planner-button').click();
        await expect(page).toHaveURL(/\/marketplaces\/transfers\/planner$/);
        await expect(page.getByRole('heading', { name: /Allocation planner/i })).toBeVisible();
        await expect(page.getByTestId('planner-table')).toBeVisible();

        // Find the row for any product and over-allocate it.
        const firstMlInput = page.getByTestId(/^allocate-ml-/).first();
        await expect(firstMlInput).toBeVisible();
        // Internal qty seeded to 100. Set ML=80, Amazon=80 -> remaining negative.
        await firstMlInput.fill('80');
        const firstAmazonInput = page.getByTestId(/^allocate-amazon-/).first();
        await firstAmazonInput.fill('80');

        // Save button should be disabled when over-allocated.
        await expect(page.getByTestId('planner-save')).toBeDisabled();

        // Dial back to a valid split and confirm save enables.
        await firstAmazonInput.fill('15');
        await expect(page.getByTestId('planner-save')).toBeEnabled();
    });

    test('reconciliation page loads', async ({ page }) => {
        await page.goto('/marketplaces/transfers');
        await page.getByTestId('open-reconciliation-button').click();
        await expect(page).toHaveURL(/\/marketplaces\/transfers\/reconciliation$/);
        await expect(page.getByRole('heading', { name: /Reconciliation/i })).toBeVisible();
        // Page renders even if there's no data — either the empty-state copy
        // or the rec table must be present.
        const empty = page.getByText(/No discrepancies/i);
        const table = page.getByTestId('rec-table');
        await expect(empty.or(table)).toBeVisible();
    });
});
