import frappe
from frappe import _


def execute():
	update_sales_invoice_remarks()
	update_purchase_invoice_remarks()


def update_sales_invoice_remarks():
	"""
	Update remarks in Sales Invoice.
	Some sites may have very large volume of sales invoices.
	In such cases, updating documents one by one won't be successful, especially during site migration step.
	Refer to the bug report: https://github.com/frappe/erpnext/issues/43634
	In this case, a bulk update must be done.

	        Step 1: Update remarks in GL Entries
	        Step 2: Update remarks in Payment Ledger Entries
	        Step 3: Update remarks in Sales Invoice	- Should be last step
	"""

	###	Step 1:	Update remarks in GL Entries
	update_sales_invoice_gle_remarks()

	###	Step 2: Update remarks in Payment Ledger Entries
	update_sales_invoice_ple_remarks()

	###	Step 3: Update remarks in Sales Invoice
	update_query = """
		UPDATE `tabSales Invoice`
		SET remarks = concat('Against Customer Order ', po_no)
		WHERE po_no <> '' AND docstatus = %(docstatus)s and remarks = %(remarks)s
	"""

	# Data for update query
	values = {"remarks": "No Remarks", "docstatus": 1}

	# Execute query
	frappe.db.sql(update_query, values=values, as_dict=0)


def update_purchase_invoice_remarks():
	"""
	Update remarks in Purchase Invoice.
	Some sites may have very large volume of purchase invoices.
	In such cases, updating documents one by one wont be successful, especially during site migration step.
	Refer to the bug report: https://github.com/frappe/erpnext/issues/43634
	In this case, a bulk update must be done.

	        Step 1: Update remarks in GL Entries
	        Step 2: Update remarks in Payment Ledger Entries
	        Step 3: Update remarks in Purchase Invoice - Should be last step
	"""

	###	Step 1:	Update remarks in GL Entries
	update_purchase_invoice_gle_remarks()

	###	Step 2:	Update remarks in Payment Ledger Entries
	update_purchase_invoice_ple_remarks()

	###	Step 3: Update remarks in Purchase Invoice
	update_query = """
		UPDATE `tabPurchase Invoice`
		SET remarks = concat('Against Supplier Invoice ', bill_no)
		WHERE bill_no <> '' AND docstatus = %(docstatus)s and remarks = %(remarks)s
	"""

	# Data for update query
	values = {"remarks": "No Remarks", "docstatus": 1}

	# Execute query
	frappe.db.sql(update_query, values=values, as_dict=0)


def update_sales_invoice_gle_remarks():
	##	Update query to update GL Entry - Updates all entries which are for Sales Invoice with No Remarks
	update_query = """
		UPDATE
		`tabGL Entry` as gle
		INNER JOIN `tabSales Invoice` as si
		ON gle.voucher_type = 'Sales Invoice' AND gle.voucher_no = si.name AND gle.remarks = %(remarks)s
		SET
		gle.remarks = concat('Against Customer Order ', si.po_no)
		WHERE si.po_no <> '' AND si.docstatus = %(docstatus)s and si.remarks = %(remarks)s
	"""

	# Data for update query
	values = {"remarks": "No Remarks", "docstatus": 1}

	# Execute query
	frappe.db.sql(update_query, values=values, as_dict=0)


def update_sales_invoice_ple_remarks():
	##	Update query to update Payment Ledger Entry - Updates all entries which are for Sales Invoice with No Remarks
	update_query = """
		UPDATE
		`tabPayment Ledger Entry` as ple
		INNER JOIN `tabSales Invoice` as si
		ON ple.voucher_type = 'Sales Invoice' AND ple.voucher_no = si.name AND ple.remarks = %(remarks)s
		SET
		ple.remarks = concat('Against Customer Order ', si.po_no)
		WHERE si.po_no <> '' AND si.docstatus = %(docstatus)s and si.remarks = %(remarks)s
	"""

	### Data for update query
	values = {"remarks": "No Remarks", "docstatus": 1}

	### Execute query
	frappe.db.sql(update_query, values=values, as_dict=0)


def update_purchase_invoice_gle_remarks():
	###	Query to update GL Entry - Updates all entries which are for Purchase Invoice with No Remarks
	update_query = """
		UPDATE
		`tabGL Entry` as gle
		INNER JOIN `tabPurchase Invoice` as pi
		ON gle.voucher_type = 'Purchase Invoice' AND gle.voucher_no = pi.name AND gle.remarks = %(remarks)s
		SET
		gle.remarks = concat('Against Supplier Invoice ', pi.bill_no)
		WHERE pi.bill_no <> '' AND pi.docstatus = %(docstatus)s and pi.remarks = %(remarks)s
	"""

	### Data for update query
	values = {"remarks": "No Remarks", "docstatus": 1}

	### Execute query
	frappe.db.sql(update_query, values=values, as_dict=0)


def update_purchase_invoice_ple_remarks():
	###	Query to update Payment Ledger Entry - Updates all entries which are for Purchase Invoice with No Remarks
	update_query = """
		UPDATE
		`tabPayment Ledger Entry` as ple
		INNER JOIN `tabPurchase Invoice` as pi
		ON ple.voucher_type = 'Purchase Invoice' AND ple.voucher_no = pi.name AND ple.remarks = %(remarks)s
		SET
		ple.remarks = concat('Against Supplier Invoice ', pi.bill_no)
		WHERE pi.bill_no <> '' AND pi.docstatus = %(docstatus)s and pi.remarks = %(remarks)s
	"""

	### Data for update query
	values = {"remarks": "No Remarks", "docstatus": 1}

	### Execute query
	frappe.db.sql(update_query, values=values, as_dict=0)
