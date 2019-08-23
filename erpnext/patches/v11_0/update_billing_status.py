# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from six import iteritems

def execute():
	frappe.reload_doctype("Sales Order")
	frappe.reload_doctype("Sales Order Item")
	frappe.reload_doctype("Delivery Note")
	frappe.reload_doctype("Delivery Note Item")
	frappe.reload_doctype("Sales Invoice")
	frappe.reload_doctype("Sales Invoice Item")

	frappe.reload_doctype("Purchase Order")
	frappe.reload_doctype("Purchase Order Item")
	frappe.reload_doctype("Purchase Receipt")
	frappe.reload_doctype("Purchase Receipt Item")
	frappe.reload_doctype("Purchase Invoice")
	frappe.reload_doctype("Purchase Invoice Item")

	for dt, detail_field in [('Delivery Note', 'dn_detail'), ('Purchase Receipt', 'pr_detail')]:
		returns = frappe.get_all("Delivery Note", filters={"is_return": 1}, fields=['name', 'return_against'])
		for return_doc in returns:
			source_details = frappe.db.sql("""
				select name, item_code, qty
				from `tab{0} Item`
				where parent = %s
			""".format(dt), return_doc.return_against, as_dict=1)

			source_items = {}
			for d in source_details:
				source_items.setdefault(d.item_code, []).append(d)

			return_details = frappe.db.sql("""
				select name, item_code, qty
				from `tab{0} Item`
				where parent = %s
			""".format(dt), return_doc.name, as_dict=1)

			for return_row in return_details:
				if return_row.item_code not in source_items:
					print("Item {0} in {1} not in {2}".format(return_row.item_code, return_doc.name, return_doc.return_against))
				else:
					valid_source = None
					for source_row in source_items[return_row.item_code]:
						if return_row.qty <= source_row.qty:
							source_row.qty -= return_row.qty
							valid_source = source_row
							break

					if valid_source:
						frappe.db.sql("update `tab{0} Item` set {1} = %s where name = %s".format(dt, detail_field),
							[valid_source.name, return_row.name])
					else:
						print("Valid Source not found for Item {0} in {1} return against {2}".format(return_row.item_code, return_doc.name, return_doc.return_against))

	si_names = frappe.get_all("Sales Invoice", {"docstatus": 1})
	for name in si_names:
		name = name.name
		doc = frappe.get_doc("Sales Invoice", name)
		doc.update_status_updater_args()
		doc.update_prevdoc_status()
		if not doc.is_return:
			doc.update_billing_status_for_zero_amount_refdoc("Sales Order")

	pi_names = frappe.get_all("Purchase Invoice", {"docstatus": 1})
	for name in pi_names:
		name = name.name
		doc = frappe.get_doc("Purchase Invoice", name)
		doc.update_status_updater_args()
		doc.update_prevdoc_status()
		if not doc.is_return:
			doc.update_billing_status_for_zero_amount_refdoc("Purchase Order")

	dn_names = frappe.get_all("Delivery Note", {"docstatus": 1})
	for name in dn_names:
		name = name.name
		doc = frappe.get_doc("Delivery Note", name)
		doc.update_prevdoc_status()

	pr_names = frappe.get_all("Purchase Receipt", {"docstatus": 1})
	for name in pr_names:
		name = name.name
		doc = frappe.get_doc("Purchase Receipt", name)
		doc.update_prevdoc_status()
