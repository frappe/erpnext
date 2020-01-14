# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json

def execute():
	existing_allow_negative_stock = frappe.db.get_value("Stock Settings", None, "allow_negative_stock")
	frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)

	head_row = ["Item Code", "Warehouse", "Quantity", "Valuation Rate"]
	stock_reco_to_be_reposted = []
	for d in frappe.db.sql("""select name, reconciliation_json from `tabStock Reconciliation`
		where docstatus=1 and creation > '2014-03-01'""", as_dict=1):
			data = json.loads(d.reconciliation_json)
			for row in data[data.index(head_row)+1:]:
				if row[3] in ["", None]:
					stock_reco_to_be_reposted.append(d.name)
					break

	for dn in stock_reco_to_be_reposted:
		reco = frappe.get_doc("Stock Reconciliation", dn)
		reco.docstatus = 2
		reco.on_cancel()

		reco.docstatus = 1
		reco.validate()
		reco.on_submit()

	frappe.db.set_value("Stock Settings", None, "allow_negative_stock", existing_allow_negative_stock)
