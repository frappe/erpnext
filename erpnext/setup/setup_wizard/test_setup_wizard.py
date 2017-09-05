# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, time
from frappe.utils.selenium_testdriver import TestDriver

def run_setup_wizard_test():
	driver = TestDriver()
	frappe.db.set_default('in_selenium', '1')

	driver.login('#page-setup-wizard')
	print('Running Setup Wizard Test...')

	# Language slide
	driver.set_select("language", "English (United Kingdom)")
	driver.wait_for_ajax(True)
	driver.wait_till_clickable(".next-btn").click()

	# Region slide
	driver.wait_for_ajax(True)
	driver.set_select("country", "India")
	driver.wait_for_ajax(True)
	driver.wait_till_clickable(".next-btn").click()

	# Profile slide
	driver.set_field("full_name", "Joe Davis")
	driver.set_field("email", "joe@example.com")
	driver.set_field("password", "somethingrandom")
	driver.wait_till_clickable(".next-btn").click()

	# Brand slide
	driver.set_select("domain", "Manufacturing")
	driver.wait_till_clickable(".next-btn").click()

	# Org slide
	driver.set_field("company_name", "Acme Corp")
	driver.wait_till_clickable(".next-btn").click()
	driver.set_field("company_tagline", "Build Tools for Builders")
	driver.set_field("bank_account", "BNL")
	driver.wait_till_clickable(".complete-btn").click()

	# Wait for desk (Lock wait timeout error)
	# driver.wait_for('#page-desktop', timeout=200)

	console = driver.get_console()
	if frappe.flags.tests_verbose:
		for line in console:
			print(line)
		print('-' * 40)
	time.sleep(1)

	frappe.db.set_default('in_selenium', None)
	driver.close()

	return True