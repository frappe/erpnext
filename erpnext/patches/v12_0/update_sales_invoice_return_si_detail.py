# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from six import iteritems

def execute():
	frappe.reload_doctype("Sales Invoice")
	frappe.reload_doctype("Sales Invoice Item")

	for dt, detail_field in [('Sales Invoice', 'si_detail')]:
		si_rows_to_update = {}
		returns = frappe.get_all(dt, filters={"is_return": 1, "return_against": ['is', 'set']}, fields=['name', 'return_against', 'update_stock', 'docstatus'])

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
				select name, item_code, qty, base_net_amount
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

						if return_doc.docstatus == 1:
							update_dict = si_rows_to_update.setdefault(valid_source.name, frappe._dict({"returned_qty": 0, "base_returned_amount": 0}))
							update_dict.base_returned_amount -= return_row.base_net_amount
							if return_doc.update_stock:
								update_dict.returned_qty -= return_row.qty
					else:
						print("Valid Source not found for Item {0} in {1} return against {2}".format(return_row.item_code, return_doc.name, return_doc.return_against))

		for row_name, update_dict in si_rows_to_update.items():
			frappe.db.set_value(dt + " Item", row_name, update_dict, None, update_modified=0)
