# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from erpnext.regional.italy.setup import make_custom_fields, setup_report
from erpnext.regional.italy import state_codes
import frappe


def execute():
	company = frappe.get_all('Company', filters = {'country': 'Italy'})
	if not company:
		return

	frappe.reload_doc('regional', 'report', 'electronic_invoice_register')
	make_custom_fields()
	setup_report()

	# Set state codes
	condition = ""
	for state, code in state_codes.items():
		condition += " when '{0}' then '{1}'".format(frappe.db.escape(state), frappe.db.escape(code))

	if condition:
		condition = "state_code = (case state {0} end),".format(condition)

	frappe.db.sql("""
		UPDATE tabAddress set {condition} country_code = UPPER(ifnull((select code
			from `tabCountry` where name = `tabAddress`.country), ''))
	""".format(condition=condition))
