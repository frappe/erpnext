from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql(
		"""
		UPDATE `tabMaterial Request`
		SET status = CASE
						WHEN per_ordered = 0 AND docstatus = 1 THEN 'Pending'
						WHEN per_ordered < 100 AND per_ordered > 0 AND docstatus = 1 THEN 'Partially Ordered'
						WHEN per_ordered = 100 AND docstatus = 1 AND material_request_type = 'Purchase' THEN 'Ordered'
						WHEN per_ordered = 100 AND docstatus = 1 AND material_request_type = 'Material Transfer' THEN 'Transferred'
						WHEN per_ordered = 100 AND docstatus = 1 AND material_request_type = 'Material Issue' THEN 'Issued'
					END
		WHERE
			status != 'Stopped' and status != 'Draft' AND status != 'Cancelled';
		"""
	)