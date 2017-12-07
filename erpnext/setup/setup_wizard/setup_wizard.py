# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from operations import install_fixtures, taxes_setup, defaults_setup, company_setup, sample_data

def setup_complete(args=None):
	if frappe.db.sql("select name from tabCompany"):
		frappe.throw(_("Setup Already Complete!!"))

	install_fixtures.install(args.get("country"))

	defaults_setup.create_price_lists(args)

	company_setup.create_fiscal_year_and_company(args)
	taxes_setup.create_sales_tax(args)

	defaults_setup.create_employee_for_self(args)
	defaults_setup.set_defaults(args)
	defaults_setup.create_territories()
	defaults_setup.create_feed_and_todo()

	company_setup.create_email_digest()

	defaults_setup.set_no_copy_fields_in_variant_settings()

	company_setup.create_website(args)

	company_setup.create_logo(args)

	frappe.local.message_log = []

	domains = args.get('domains')
	domain_settings = frappe.get_single('Domain Settings')
	domain_settings.set_active_domains(domains)

	frappe.db.commit()
	login_as_first_user(args)

	frappe.db.commit()
	frappe.clear_cache()

	try:
		sample_data.make_sample_data(domains)
		frappe.clear_cache()
	except:
		# clear message
		if frappe.message_log:
			frappe.message_log.pop()

		pass

def login_as_first_user(args):
	if args.get("email") and hasattr(frappe.local, "login_manager"):
		frappe.local.login_manager.login_as(args.get("email"))
