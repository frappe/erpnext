import frappe
from frappe.query_builder import DocType


def execute():
	qlr = DocType("Quotation Lost Reason Detail")
	quotation = DocType("Quotation")

	sub_query = frappe.qb.from_(quotation).select(quotation.name)
	query = frappe.qb.from_(qlr).delete().where(qlr.parent.notin(sub_query))
	query.run()
