# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute():
	frappe.reload_doctype("Stock Entry")
	frappe.reload_doctype("Stock Entry Detail")
	frappe.reload_doctype("Landed Cost Taxes and Charges")

	frappe.db.sql("""update `tabStock Entry Detail` sed, `tabStock Entry` se
		set sed.valuation_rate=sed.incoming_rate, sed.basic_rate=sed.incoming_rate, sed.basic_amount=sed.amount
		where sed.parent = se.name
		and (se.purpose not in ('Manufacture', 'Repack') or ifnull(additional_operating_cost, 0)=0)
	""")

	stock_entries = frappe.db.sql_list("""select name from `tabStock Entry`
		where purpose in ('Manufacture', 'Repack') and ifnull(additional_operating_cost, 0)!=0
		and docstatus < 2""")

	for d in stock_entries:
		stock_entry = frappe.get_doc("Stock Entry", d)
		stock_entry.append("additional_costs", {
			"description": "Additional Operating Cost",
			"amount": stock_entry.additional_operating_cost
		})

		number_of_fg_items = len([t.t_warehouse for t in stock_entry.get("items") if t.t_warehouse])

		for d in stock_entry.get("items"):
			d.valuation_rate = d.incoming_rate

			if d.bom_no or (d.t_warehouse and number_of_fg_items == 1):
				d.additional_cost = stock_entry.additional_operating_cost

			d.basic_rate = flt(d.valuation_rate) - flt(d.additional_cost)
			d.basic_amount = flt(flt(d.basic_rate) *flt(d.transfer_qty), d.precision("basic_amount"))

		stock_entry.flags.ignore_validate = True
		stock_entry.flags.ignore_validate_update_after_submit = True
		stock_entry.save()
