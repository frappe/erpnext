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
	time.sleep(1)

	driver.set_select("language", "English (United States)")
	driver.wait_for_ajax(True)
	time.sleep(1)
	driver.click(".next-btn")

	# Region slide
	driver.wait_for_ajax(True)
	driver.set_select("country", "India")
	driver.wait_for_ajax(True)
	time.sleep(1)
	driver.click(".next-btn")

	# Profile slide
	driver.set_field("full_name", "Great Tester")
	driver.set_field("email", "great@example.com")
	driver.set_field("password", "test")
	driver.wait_for_ajax(True)
	time.sleep(1)
	driver.click(".next-btn")
	time.sleep(1)

	# domain slide
	driver.set_multicheck("domains", ["Manufacturing"])
	time.sleep(1)
	driver.click(".next-btn")

	# Org slide
	driver.set_field("company_name", "For Testing")
	time.sleep(1)
	driver.print_console()
	driver.click(".next-btn")

	driver.set_field("company_tagline", "Just for GST")
	driver.set_field("bank_account", "HDFC")
	time.sleep(3)
	driver.click(".complete-btn")

	# Wait for desktop
	driver.wait_for('#page-desktop', timeout=600)

	driver.print_console()
	time.sleep(3)

	frappe.db.set_default('in_selenium', None)
	frappe.db.set_value("Company", "For Testing", "write_off_account", "Write Off - FT")
	frappe.db.set_value("Company", "For Testing", "exchange_gain_loss_account", "Exchange Gain/Loss - FT")
	frappe.db.commit()

	driver.close()

	return True
