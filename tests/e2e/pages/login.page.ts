import { Page } from '@playwright/test';

export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/');
  }

  async login(username: string, password: string) {
    // Fill email field
    await this.page.getByRole('textbox', { name: 'Email', exact: true }).fill(username);
    
    // Fill password field
    await this.page.getByRole('textbox', { name: 'Password' }).fill(password);
    
    // Click login button
    await this.page.getByRole('button', { name: 'Login' }).click();
    
    // Wait for navigation to complete (home page or dashboard)
    await this.page.waitForURL(/.*\/(app|home)/);
  }

  async isLoginPageVisible() {
    return await this.page.getByRole('heading', { name: 'Login to KanaanERP' }).isVisible();
  }
}