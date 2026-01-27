import json

import frappe

from erpnext.manufacturing.doctype.slab.api import checkout_slab
from erpnext.manufacturing.page.operator_station.operator_station import finish_distribution


@frappe.whitelist()
def create_slab_quality_report(report: str | dict, shift: str, job_card: str):
	if isinstance(report, str):
		report = json.loads(report)

	finish_distribution(job_card, "Quality Analysis")
	doc = frappe.new_doc("Slab Quality Report")
	doc.update(report)
	doc.shift = shift

	# TODO: Remove these after testing.
	doc.insert(ignore_permissions=True)
	doc.submit()

	if doc.slab:
		checkout_slab(doc.slab)
	

	return doc
