import frappe
from frappe.utils import create_batch

BATCH_SIZE = 500


def execute():
	"""Move 'Set rate of sub-assembly item based on BOM' from BOM (parent) to BOM Item (per row).

	The new BOM Item column is created with default 1, so after the schema sync every existing row
	already reads 1. Only the rows under BOMs that had the setting turned OFF need correcting to 0,
	so we touch just that minority instead of rewriting every component row -- and do it in batches
	so large installs never run a single table-locking update.
	"""
	if not frappe.db.has_column("BOM", "set_rate_of_sub_assembly_item_based_on_bom"):
		return

	bom = frappe.qb.DocType("BOM")
	off_boms = (
		frappe.qb.from_(bom).select(bom.name).where(bom.set_rate_of_sub_assembly_item_based_on_bom == 0)
	).run(pluck=True)
	if not off_boms:
		return

	bom_item = frappe.qb.DocType("BOM Item")
	for batch in create_batch(off_boms, BATCH_SIZE):
		(
			frappe.qb.update(bom_item)
			.set(bom_item.set_rate_of_sub_assembly_item_based_on_bom, 0)
			.where(bom_item.parent.isin(batch))
		).run()
		frappe.db.commit()  # keep each batch a small, independent transaction
