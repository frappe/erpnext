import frappe


def execute():
	update_purchase_invoices()
	update_sales_invoices()
	update_sales_debit_notes()


def update_purchase_invoices():
	invoices = frappe.get_all(
		"Purchase Invoice",
		filters={"docstatus": 1, "is_return": 0},
		pluck="name",
	)

	if not invoices:
		return

	update_gl_entry(doctype="Purchase Invoice", invoices=invoices, value="Purchase Invoice")


def update_sales_invoices():
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "is_return": 0, "is_debit_note": 0},
		pluck="name",
	)
	if not invoices:
		return

	update_gl_entry(doctype="Sales Invoice", invoices=invoices, value="Sales Invoice")


def update_sales_debit_notes():
	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "is_debit_note": 1},
		pluck="name",
	)

	if not invoices:
		return

	update_gl_entry(doctype="Sales Invoice", invoices=invoices, value="Debit Note")


def update_gl_entry(doctype, invoices, value):
	gl_entry = frappe.qb.DocType("GL Entry")
	(
		frappe.qb.update(gl_entry)
		.set("voucher_subtype", value)
		.where(gl_entry.voucher_subtype.isnotnull())
		.where(gl_entry.voucher_no.isin(invoices))
		.where(gl_entry.voucher_type == doctype)
		.run()
	)
