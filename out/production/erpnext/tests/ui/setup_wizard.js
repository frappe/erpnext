const path = require('path');
const path_join = path.resolve;
const apps_path = path_join(__dirname, '..', '..', '..', '..');
const frappe_ui_tests_path = path_join(apps_path, 'frappe', 'frappe', 'tests', 'ui');

const login = require(frappe_ui_tests_path + "/login.js")['Login'];
const welcome = require(frappe_ui_tests_path + "/setup_wizard.js")['Welcome'];
const region = require(frappe_ui_tests_path + "/setup_wizard.js")['Region'];
const user = require(frappe_ui_tests_path + "/setup_wizard.js")['User'];

module.exports = {
	before: browser => {
		browser
			.url(browser.launch_url + '/login')
			.waitForElementVisible('body', 5000);
	},
	'Login': login,
	'Welcome': welcome,
	'Region': region,
	'User': user,
	'Domain': browser => {
		let slide_selector = '[data-slide-name="domain"]';
		browser
			.waitForElementVisible(slide_selector, 2000)
			.setValue('select[data-fieldname="domain"]', "Manufacturing")
			.click(slide_selector + ' .next-btn');
	},
	'Brand': browser => {
		let slide_selector = '[data-slide-name="brand"]';
		browser
			.waitForElementVisible(slide_selector, 2000)
			.setValue('input[data-fieldname="company_name"]', "Acme")
			.click(slide_selector + " .next-btn");
	},
	'Organisation': browser => {
		let slide_selector = '[data-slide-name="organisation"]';
		browser
			.waitForElementVisible(slide_selector, 2000)
			.setValue('input[data-fieldname="company_tagline"]', "Build tools for Builders")
			.setValue('input[data-fieldname="bank_account"]', "YNG")
			.click(slide_selector + " .next-btn");
	},

	after: browser => {
		browser.end();
	},
};
