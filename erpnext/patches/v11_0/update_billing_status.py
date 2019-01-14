# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	si_names = frappe.get_all("Sales Invoice", {"docstatus": 1})
	for name in si_names:
		name = name.name
		doc = frappe.get_doc("Sales Invoice", name)
		doc.update_status_updater_args()
		doc.update_prevdoc_status()
		doc.update_billing_status_in_dn()
		if not doc.is_return:
			doc.update_billing_status_for_zero_amount_refdoc("Sales Order")

	pi_names = frappe.get_all("Purchase Invoice", {"docstatus": 1})
	for name in pi_names:
		name = name.name
		doc = frappe.get_doc("Purchase Invoice", name)
		doc.update_status_updater_args()
		doc.update_prevdoc_status()
		doc.update_billing_status_in_pr()
		if not doc.is_return:
			doc.update_billing_status_for_zero_amount_refdoc("Purchase Order")
