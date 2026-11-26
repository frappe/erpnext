import frappe


def execute():
	reference = frappe.qb.DocType("Payment Entry Reference").as_("reference")
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
		(
			frappe.qb.update(reference)
			.join(source)
			.on(source.name == reference.reference_name)
			.set(reference.posting_date, source[date_field])
			.where((reference.reference_doctype == doctype) & reference.posting_date.isnull())
		).run()


def get_date_field(doctype):
	if not doctype or not frappe.db.table_exists(doctype):
		return

	for fieldname in ("posting_date", "transaction_date"):
		if frappe.db.has_column(doctype, fieldname):
			return fieldname
