# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import (
	get_data,
)


def execute():
	data = []

	for company in frappe.db.get_list("Company", pluck="name"):
		data += get_data(
			frappe._dict(
				{
					"company": company,
				}
			)
		)

	if data:
		for d in data:
			if d and d.get("voucher_type") == "Subcontracting Receipt":
				doc = frappe.new_doc("Repost Item Valuation")
				doc.voucher_type = d.get("voucher_type")
				doc.voucher_no = d.get("voucher_no")
				doc.save()
				doc.submit()
