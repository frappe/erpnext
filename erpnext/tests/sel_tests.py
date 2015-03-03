# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""
Run Selenium Tests

Requires a clean install. After reinstalling fresh db, call

	frappe --execute erpnext.tests.sel_tests.start

"""

from __future__ import unicode_literals
import frappe

from frappe.utils import sel
import time

def start():
	try:
		run()
	finally:
		sel.close()

def run():
	def next_slide(idx, selector="next-btn"):
		sel.find('[data-slide-id="{0}"] .{1}'.format(idx, selector))[0].click()
		sel.wait_for_ajax()


	sel.start(verbose=True, driver="Firefox")
	sel.input_wait = 0.2
	sel.login("#page-setup-wizard")

	# slide 1
	next_slide("0")

	sel.set_field("first_name", "Test")
	sel.set_field("last_name", "User")
	sel.set_field("email", "test@erpnext.com")
	sel.set_field("password", "test")

	next_slide("1")

	sel.set_select("country", "India")

	next_slide("2")

	sel.set_field("company_name", "Wind Power LLC")
	sel.set_field("fy_start_date", "01-04-2014")
	sel.set_field("company_tagline", "Wind Power For Everyone")

	next_slide("3")
	next_slide("4")

	sel.set_field("tax_1", "VAT")
	sel.set_field("tax_rate_1", "12.5")

	sel.set_field("tax_2", "Service Tax")
	sel.set_field("tax_rate_2", "10.36")

	next_slide("5")

	sel.set_field("customer_1", "Asian Junction")
	sel.set_field("customer_contact_1", "January Vaclavik")
	sel.set_field("customer_2", "Life Plan Counselling")
	sel.set_field("customer_contact_2", "Jana Tobeolisa")
	sel.set_field("customer_3", "Two Pesos")
	sel.set_field("customer_contact_3", "Satomi Shigeki")
	sel.set_field("customer_4", "Intelacard")
	sel.set_field("customer_contact_4", "Hans Rasmussen")

	next_slide("6")

	sel.set_field("item_1", "Wind Turbine A")
	sel.set_field("item_2", "Wind Turbine B")
	sel.set_field("item_3", "Wind Turbine C")

	next_slide("7")

	sel.set_field("supplier_1", "Helios Air")
	sel.set_field("supplier_contact_1", "Quimey Osorio")
	sel.set_field("supplier_2", "Ks Merchandise")
	sel.set_field("supplier_contact_2", "Edgarda Salcedo")
	sel.set_field("supplier_3", "Eagle Hardware")
	sel.set_field("supplier_contact_3", "Hafsteinn Bjarnarsonar")

	next_slide("8")

	sel.set_field("item_buy_1", "Bearing Pipe")
	sel.set_field("item_buy_2", "Bearing Assembly")
	sel.set_field("item_buy_3", "Base Plate")
	sel.set_field("item_buy_4", "Coil")

	next_slide("9", "complete-btn")

	sel.wait('[data-state="setup-complete"]')

	w = raw_input("quit?")

# complete setup
# new customer
# new supplier
# new item
# sales cycle
# purchase cycle
