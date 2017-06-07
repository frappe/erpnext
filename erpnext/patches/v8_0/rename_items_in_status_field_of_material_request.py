from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql(
		"""
		UPDATE `tabMaterial Request`
			SET status = CASE
							WHEN docstatus = 2 THEN 'Cancelled'
							WHEN docstatus = 0 THEN 'Draft'
							ELSE CASE
								WHEN status = 'Stopped' THEN 'Stopped'
								WHEN status != 'Stopped' AND per_ordered = 0 THEN 'Pending'
								WHEN per_ordered < 100 AND per_ordered > 0 AND status != 'Stopped'
									THEN 'Partially Ordered'
								WHEN per_ordered = 100 AND material_request_type = 'Purchase'
									AND status != 'Stopped' THEN 'Ordered'
								WHEN per_ordered = 100 AND material_request_type = 'Material Transfer'
									AND status != 'Stopped' THEN 'Transferred'
								WHEN per_ordered = 100 AND material_request_type = 'Material Issue'
									AND status != 'Stopped' THEN 'Issued'
							END
			END
		"""
	)