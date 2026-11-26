import frappe
from pypika.terms import Bracket


def execute():
	reference = frappe.qb.DocType("Payment Entry Reference")
	reference_doctypes = (
		frappe.qb.from_(reference)
		.select(reference.reference_doctype)
		.distinct()
		.where(reference.posting_date.isnull())
		.run(pluck=True)
	)

	for doctype in reference_doctypes:
		date_field = get_date_field(doctype)
		if not date_field:
			continue

		source = frappe.qb.DocType(doctype)
		source_date = (
			frappe.qb.from_(source).select(source[date_field]).where(source.name == reference.reference_name)
		)
		(
			frappe.qb.update(reference)
			.set(reference.posting_date, Bracket(source_date))
			.where((reference.reference_doctype == doctype) & reference.posting_date.isnull())
		).run()


def get_date_field(doctype):
	if not doctype or not frappe.db.table_exists(doctype):
		return

	for fieldname in ("posting_date", "transaction_date"):
		if frappe.db.has_column(doctype, fieldname):
			return fieldname
