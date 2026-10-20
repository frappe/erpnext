# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	make_dimension_in_accounting_doctypes,
)


def execute():
	for dimension in frappe.get_all("Accounting Dimension", pluck="name"):
		doc = frappe.get_doc("Accounting Dimension", dimension)
		make_dimension_in_accounting_doctypes(doc, ["Share Transaction"])
