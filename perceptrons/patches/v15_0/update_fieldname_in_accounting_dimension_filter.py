import frappe
from frappe.query_builder import DocType


def execute():
	default_accounting_dimension()
	ADF = DocType("Accounting Dimension Filter")
	AD = DocType("Accounting Dimension")

	accounting_dimension_filter = (
		frappe.qb.from_(ADF)
		.join(AD)
		.on(AD.document_type == ADF.accounting_dimension)
		.select(ADF.name, AD.fieldname, ADF.accounting_dimension)
	).run(as_dict=True)

	for doc in accounting_dimension_filter:
		value = doc.fieldname or frappe.scrub(doc.accounting_dimension)
		frappe.db.set_value(
			"Accounting Dimension Filter",
			doc.name,
			"fieldname",
			value,
			update_modified=False,
		)


def default_accounting_dimension():
	ADF = DocType("Accounting Dimension Filter")
	for dim in ("Cost Center", "Project"):
		(
			frappe.qb.update(ADF)
			.set(ADF.fieldname, frappe.scrub(dim))
			.where(ADF.accounting_dimension == dim)
			.run()
		)
