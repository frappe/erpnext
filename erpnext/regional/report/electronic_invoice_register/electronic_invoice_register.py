# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.accounts.report.sales_register.sales_register import _execute
from erpnext.accounts.report.utils import validate_date_range


def execute(filters=None):
	validate_date_range(filters)

	if not (filters or {}).get("company"):
		frappe.throw(_("Please select a Company"))

	return _execute(filters)
