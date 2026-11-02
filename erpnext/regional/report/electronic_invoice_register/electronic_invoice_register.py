# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from erpnext.accounts.report.sales_register.sales_register import _execute
from erpnext.accounts.report.utils import validate_date_range


def execute(filters=None):
<<<<<<< HEAD
=======
	validate_date_range(filters)

	if not (filters or {}).get("company"):
		frappe.throw(_("Please select a Company"))

>>>>>>> 5fcdcf1 (fix(reports): validate report date ranges)
	return _execute(filters)
