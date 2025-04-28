# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

<<<<<<< HEAD
=======
# test_records = frappe.get_test_records('Designation')

>>>>>>> 7c4cf3e834 (Favicon.svg)

def create_designation(**args):
	args = frappe._dict(args)
	if frappe.db.exists("Designation", args.designation_name or "_Test designation"):
		return frappe.get_doc("Designation", args.designation_name or "_Test designation")

	designation = frappe.get_doc(
		{
			"doctype": "Designation",
			"designation_name": args.designation_name or "_Test designation",
			"description": args.description or "_Test description",
		}
	)
	designation.save()
	return designation
