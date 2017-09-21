# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, time
from frappe.utils.selenium_testdriver import TestDriver

def run_setup_wizard_test():
	driver = TestDriver()
	frappe.db.set_default('in_selenium', '1')
	frappe.db.commit()

	driver.login('#page-setup-wizard')
	print('Running Setup Wizard Test...')

	# Language slide
	driver.wait_for_ajax(True)
	time.sleep(2)
	driver.set_select("language", "English (United States)")
	driver.wait_for_ajax(True)
	driver.wait_till_clickable(".next-btn").click()

	# Region slide
	driver.wait_for_ajax(True)
	driver.set_select("country", "India")
	driver.wait_for_ajax(True)
	driver.wait_till_clickable(".next-btn").click()

	# Profile slide
	driver.set_field("full_name", "Great Tester")
	driver.set_field("email", "great@example.com")
	driver.set_field("password", "test")
	driver.wait_till_clickable(".next-btn").click()

	# Brand slide
	driver.set_select("domain", "Manufacturing")
	time.sleep(5)
	driver.wait_till_clickable(".next-btn").click()

	# Org slide
	driver.set_field("company_name", "For Testing")
	driver.wait_till_clickable(".next-btn").click()
	driver.set_field("company_tagline", "Just for GST")
	driver.set_field("bank_account", "HDFC")
	driver.wait_till_clickable(".complete-btn").click()

	# Wait for desktop
	driver.wait_for('#page-desktop', timeout=600)

	console = driver.get_console()
	if frappe.flags.tests_verbose:
		for line in console:
			print(line)
		print('-' * 40)
	time.sleep(1)

	frappe.db.set_default('in_selenium', None)
	frappe.db.set_value("Company", "For Testing", "write_off_account", "Write Off - FT")
	frappe.db.set_value("Company", "For Testing", "exchange_gain_loss_account", "Exchange Gain/Loss - FT")
	frappe.db.commit()

	driver.close()

	return True
