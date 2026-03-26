import frappe
from frappe.query_builder.functions import Sum


def execute():
	MaterialRequestItem = frappe.qb.DocType("Material Request Item")

	mri_query = (
		frappe.qb.from_(MaterialRequestItem)
		.select(MaterialRequestItem.packed_item, Sum(MaterialRequestItem.qty))
		.where((MaterialRequestItem.packed_item.isnotnull()) & (MaterialRequestItem.docstatus == 1))
		.groupby(MaterialRequestItem.packed_item)
	)

	mri_data = mri_query.run()

	if not mri_data:
		return

	updates_against_mr = {data[0]: {"requested_qty": data[1]} for data in mri_data}

	frappe.db.auto_commit_on_many_writes = True
	frappe.db.bulk_update("Packed Item", updates_against_mr)
	frappe.db.auto_commit_on_many_writes = False
