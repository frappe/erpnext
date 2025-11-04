import { Page } from '@playwright/test';

export class DashboardPage {
  constructor(private page: Page) {}

  async isLoggedIn() {
    // Check if User Menu button is visible - indicates successful login
    return await this.page.getByRole('button', { name: 'User Menu' }).isVisible();
  }

  async getUserName() {
    // Get the logged-in user name from the User Menu
    const userButton = this.page.getByRole('button', { name: 'User Menu' });
    return await userButton.textContent();
  }

  async navigateToModule(moduleName: string) {
    // Navigate to a module by clicking its link in the sidebar
    await this.page.getByRole('link', { name: moduleName }).first().click();
    await this.page.waitForURL(/.*\/app\/.*/);
  }

  async isModuleVisible(moduleName: string) {
    return await this.page.getByRole('link', { name: moduleName }).first().isVisible();
  }

  async getModuleTitle() {
    // Get the current module title from the page heading
    const heading = this.page.locator('h3').first();
    return await heading.textContent();
  }

  async isSearchBoxVisible() {
    return await this.page.getByRole('combobox', { name: /Search or type a command/ }).isVisible();
  }

  async isNotificationButtonVisible() {
    return await this.page.getByRole('button', { name: /notifications/ }).isVisible();
  }

  async hasMainContent() {
    // Check if main content area is visible
    return await this.page.locator('main').isVisible();
  }

  async isRTLLayout() {
    // Check if page is using RTL layout (data-dir or direction attribute)
    const htmlDir = await this.page.locator('html').evaluate(el => el.getAttribute('dir'));
    return htmlDir === 'rtl';
  }
}