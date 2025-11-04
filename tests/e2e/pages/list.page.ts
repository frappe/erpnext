import { Page } from '@playwright/test';

export class ListPage {
  constructor(private page: Page) {}

  async getListTitle() {
    // Get the list view title
    const heading = this.page.locator('h3').first();
    return await heading.textContent();
  }

  async getRecordCount() {
    // Extract the number of records from the counter (e.g., "3 من 3")
    const counter = this.page.locator('[class*="list-count"]').first();
    const text = await counter.textContent();
    // Parse number from text like "3 من 3"
    const match = text?.match(/(\d+)/);
    return match ? parseInt(match[1]) : 0;
  }

  async hasRecords() {
    // Check if any records are visible in the list
    return await this.page.locator('main').locator('a[href*="/app/"]').first().isVisible();
  }

  async getFirstRecordName() {
    // Get the name of the first record in the list
    const firstRecord = this.page.locator('main').locator('a[href*="/app/"]').first();
    return await firstRecord.textContent();
  }

  async clickFirstRecord() {
    // Click on the first record to open it
    const firstRecord = this.page.locator('main').locator('a[href*="/app/"]').first();
    await firstRecord.click();
    // Wait for the detail page to load
    await this.page.waitForURL(/.*\/app\/[a-z]+\/.*/, { timeout: 5000 });
  }

  async isAddButtonVisible() {
    // Check if "Add" or "Create" button is visible
    return await this.page.getByRole('button', { name: /إضافة|انشاء|Add|Create/i }).first().isVisible();
  }

  async isFilterPanelVisible() {
    // Check if filter panel is visible
    return await this.page.getByText(/Filter|منقي/i).first().isVisible();
  }

  async hasListViewControls() {
    // Check if list view has basic controls (filters, sort, etc.)
    const filterBtn = await this.isFilterPanelVisible();
    const addBtn = await this.isAddButtonVisible();
    return filterBtn || addBtn;
  }
}