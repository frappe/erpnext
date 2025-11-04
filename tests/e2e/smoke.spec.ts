import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/login.page';
import { DashboardPage } from './pages/dashboard.page';
import { ListPage } from './pages/list.page';

/**
 * Kanaan ERP - Comprehensive Smoke Test Suite
 * 
 * This test suite verifies core functionality of the ERPNext/Kanaan ERP application:
 * 1. Login flow
 * 2. Dashboard accessibility
 * 3. Module navigation
 * 4. List view functionality
 * 5. Record detail view
 * 6. Arabic RTL layout support
 * 7. Key UI components
 */

test.describe('Kanaan ERP - Full Smoke Test', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;
  let listPage: ListPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
    listPage = new ListPage(page);
  });

  test('should load login page successfully', async ({ page }) => {
    // Navigate to application
    await loginPage.goto();
    
    // Verify login page is displayed
    const isLoginVisible = await loginPage.isLoginPageVisible();
    expect(isLoginVisible).toBeTruthy();
    
    // Verify page title contains "Login"
    expect(page.url()).toContain('login');
  });

  test('should login with valid credentials', async ({ page }) => {
    // Navigate to login page
    await loginPage.goto();
    
    // Perform login
    await loginPage.login('Administrator', 'admin');
    
    // Verify user is logged in (User Menu button is visible)
    const isLoggedIn = await dashboardPage.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
    
    // Verify user name in menu
    const userName = await dashboardPage.getUserName();
    expect(userName).toContain('Administrator');
  });

  test('should display dashboard after login', async ({ page }) => {
    // Perform login flow
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Verify main content is visible
    const hasContent = await dashboardPage.hasMainContent();
    expect(hasContent).toBeTruthy();
    
    // Verify navigation is visible
    const isSearchVisible = await dashboardPage.isSearchBoxVisible();
    expect(isSearchVisible).toBeTruthy();
    
    // Verify notification button is visible
    const isNotificationVisible = await dashboardPage.isNotificationButtonVisible();
    expect(isNotificationVisible).toBeTruthy();
  });

  test('should display RTL layout for Arabic interface', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Check if layout is RTL (Right-to-Left for Arabic)
    const isRTL = await dashboardPage.isRTLLayout();
    expect(isRTL).toBeTruthy();
  });

  test('should have all key modules visible', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Verify key modules are visible in sidebar
    const modules = [
      'المحاسبة',      // Accounting (Arabic)
      'المشتريات',    // Buying (Arabic)
      'المبيعات',     // Selling (Arabic)
      'المخازن',      // Stock (Arabic)
    ];
    
    for (const moduleName of modules) {
      const isVisible = await dashboardPage.isModuleVisible(moduleName);
      expect(isVisible).toBeTruthy();
    }
  });

  test('should navigate to Customer module', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to Customer module
    await dashboardPage.navigateToModule('العميل'); // "Customer" in Arabic
    
    // Verify page navigated to customer list
    expect(page.url()).toContain('/app/customer');
  });

  test('should display customer list with records', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to Customer module
    await dashboardPage.navigateToModule('العميل');
    
    // Wait for list to load
    await page.waitForLoadState('networkidle');
    
    // Verify list has records
    const hasRecords = await listPage.hasRecords();
    expect(hasRecords).toBeTruthy();
    
    // Verify list title
    const title = await listPage.getListTitle();
    expect(title).toContain('العميل'); // "Customer" in Arabic
  });

  test('should open customer record from list', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to Customer module
    await dashboardPage.navigateToModule('العميل');
    await page.waitForLoadState('networkidle');
    
    // Get first customer name before clicking
    const firstCustomerName = await listPage.getFirstRecordName();
    
    // Click first record
    await listPage.clickFirstRecord();
    
    // Verify we're on a customer detail page
    expect(page.url()).toContain('/app/customer/');
    
    // Verify the customer name is displayed in the page
    const pageContent = await page.content();
    expect(pageContent).toContain(firstCustomerName);
  });

  test('should display customer detail form with tabs', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to Customer module
    await dashboardPage.navigateToModule('العميل');
    await page.waitForLoadState('networkidle');
    
    // Open first customer
    await listPage.clickFirstRecord();
    await page.waitForLoadState('networkidle');
    
    // Verify detail form tabs are visible
    const tabsLocator = page.locator('tablist').first();
    const isTabsVisible = await tabsLocator.isVisible();
    expect(isTabsVisible).toBeTruthy();
    
    // Verify form fields are visible
    const formFields = page.locator('input[type="text"]').first();
    const isFormFieldVisible = await formFields.isVisible();
    expect(isFormFieldVisible).toBeTruthy();
  });

  test('should have customer tabs and sections', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to Customer module
    await dashboardPage.navigateToModule('العميل');
    await page.waitForLoadState('networkidle');
    
    // Open first customer
    await listPage.clickFirstRecord();
    await page.waitForLoadState('networkidle');
    
    // Verify key tabs exist
    const expectedTabs = [
      'تفاصيل',                    // Details
      'معلومات الاتصال والعنوان',  // Contact & Address
      'المحاسبة',                  // Accounting
    ];
    
    for (const tabName of expectedTabs) {
      const tabElement = page.getByRole('tab', { name: tabName }).first();
      const isVisible = await tabElement.isVisible();
      expect(isVisible).toBeTruthy();
    }
  });

  test('should display activity and comments section', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to Customer module
    await dashboardPage.navigateToModule('العميل');
    await page.waitForLoadState('networkidle');
    
    // Open first customer
    await listPage.clickFirstRecord();
    await page.waitForLoadState('networkidle');
    
    // Verify activity section is visible
    const activityHeading = page.getByRole('heading', { name: /نشاط|Activity/ });
    const isActivityVisible = await activityHeading.first().isVisible();
    expect(isActivityVisible).toBeTruthy();
    
    // Verify comments section is visible
    const commentsHeading = page.getByRole('heading', { name: /تعليقات|Comments/ });
    const isCommentsVisible = await commentsHeading.first().isVisible();
    expect(isCommentsVisible).toBeTruthy();
  });

  test('should have functional list view controls', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to Customer module
    await dashboardPage.navigateToModule('العميل');
    await page.waitForLoadState('networkidle');
    
    // Verify list controls are present
    const hasControls = await listPage.hasListViewControls();
    expect(hasControls).toBeTruthy();
    
    // Verify Add button is visible
    const addBtnVisible = await listPage.isAddButtonVisible();
    expect(addBtnVisible).toBeTruthy();
    
    // Verify filter controls are visible
    const filterVisible = await listPage.isFilterPanelVisible();
    expect(filterVisible).toBeTruthy();
  });

  test('should navigate back to home', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to Customer module
    await dashboardPage.navigateToModule('العميل');
    await page.waitForLoadState('networkidle');
    
    // Click on Home link to go back
    await dashboardPage.navigateToModule('الصفحة الرئيسية'); // Home
    
    // Verify we're back on home
    expect(page.url()).toContain('/app/home');
  });

  test('should verify application stability under navigation', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate between multiple modules
    const modulesSequence = [
      'المبيعات',    // Selling
      'المشتريات',   // Buying
      'المخازن',     // Stock
      'المحاسبة',    // Accounting
      'الصفحة الرئيسية', // Home
    ];
    
    for (const moduleName of modulesSequence) {
      await dashboardPage.navigateToModule(moduleName);
      await page.waitForLoadState('networkidle');
      
      // Verify navigation was successful
      const hasContent = await dashboardPage.hasMainContent();
      expect(hasContent).toBeTruthy();
    }
  });

  test('should handle page refresh without losing login', async ({ page }) => {
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Verify logged in
    let isLoggedIn = await dashboardPage.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
    
    // Refresh the page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Verify still logged in after refresh
    isLoggedIn = await dashboardPage.isLoggedIn();
    expect(isLoggedIn).toBeTruthy();
  });

  test('should load application without console errors', async ({ page }) => {
    // Listen for console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Perform login
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    // Navigate to a module
    await dashboardPage.navigateToModule('العميل');
    await page.waitForLoadState('networkidle');
    
    // Open a record
    await listPage.clickFirstRecord();
    await page.waitForLoadState('networkidle');
    
    // Filter out expected socket.io connection errors and other known warnings
    const criticalErrors = consoleErrors.filter(error => 
      !error.includes('socket.io') &&
      !error.includes('Synchronous XMLHttpRequest') &&
      !error.includes('deprecated')
    );
    
    // Verify no critical errors
    expect(criticalErrors.length).toBe(0);
  });
});

test.describe('Kanaan ERP - Performance Baseline', () => {
  test('should load home page within acceptable time', async ({ page }, testInfo) => {
    const startTime = Date.now();
    
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    const loadTime = Date.now() - startTime;
    
    // Verify page loaded within 10 seconds (including login)
    expect(loadTime).toBeLessThan(10000);
    
    // Log performance metric
    testInfo.annotations.push({
      type: 'performance',
      description: `Login and dashboard load time: ${loadTime}ms`
    });
  });

  test('should load customer list within acceptable time', async ({ page }, testInfo) => {
    const loginPage = new LoginPage(page);
    const dashboardPage = new DashboardPage(page);
    const listPage = new ListPage(page);
    
    await loginPage.goto();
    await loginPage.login('Administrator', 'admin');
    
    const startTime = Date.now();
    
    await dashboardPage.navigateToModule('العميل');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // Verify list loaded within 5 seconds
    expect(loadTime).toBeLessThan(5000);
    
    // Verify records are present
    const hasRecords = await listPage.hasRecords();
    expect(hasRecords).toBeTruthy();
    
    testInfo.annotations.push({
      type: 'performance',
      description: `Customer list load time: ${loadTime}ms`
    });
  });
});