import json

import frappe

from erpnext.manufacturing.doctype.slab.api import checkout_slab


@frappe.whitelist()
def create_slab_quality_report(report: str | dict):
	if isinstance(report, str):
		report = json.loads(report)

	doc = frappe.new_doc("Slab Quality Report")
	doc.update(report)

	# TODO: Remove these after testing.
	doc.insert(ignore_permissions=True)
	doc.submit(ignore_permissions=True)

	if doc.slab:
		checkout_slab(doc.slab)

	return doc
