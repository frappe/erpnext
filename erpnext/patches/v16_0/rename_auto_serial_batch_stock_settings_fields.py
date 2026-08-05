import frappe
from frappe import qb


def execute():
	renames = {
		"auto_create_serial_and_batch_bundle_for_outward": "auto_create_serial_batch_entries_for_outward",
		"do_not_update_serial_batch_on_creation_of_auto_bundle": "do_not_update_serial_batch_on_auto_creation",
	}

	singles = qb.DocType("Singles")
	for old_field, new_field in renames.items():
		(
			qb.update(singles)
			.set(singles.field, new_field)
			.where((singles.doctype == "Stock Settings") & (singles.field == old_field))
			.run()
		)
		frappe.db.delete("DefaultValue", {"defkey": old_field})

	# Dropped outright - naming is no longer configurable now that there is no bundle to name.
	dropped = "set_serial_and_batch_bundle_naming_based_on_naming_series"
	(
		qb.from_(singles)
		.delete()
		.where((singles.doctype == "Stock Settings") & (singles.field == dropped))
		.run()
	)
	frappe.db.delete("DefaultValue", {"defkey": dropped})

	frappe.delete_doc_if_exists("Print Format", "Purchase Receipt Serial and Batch Bundle Print")
