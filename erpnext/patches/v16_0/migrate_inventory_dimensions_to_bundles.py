import frappe
from frappe.query_builder import Criterion
from frappe.utils import flt

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions

# Voucher type -> its stock items child doctype (for linking the migrated bundle back to the row).
ITEM_TABLE = {
	"Stock Entry": "Stock Entry Detail",
	"Purchase Receipt": "Purchase Receipt Item",
	"Purchase Invoice": "Purchase Invoice Item",
	"Delivery Note": "Delivery Note Item",
	"Sales Invoice": "Sales Invoice Item",
	"POS Invoice": "POS Invoice Item",
	"Stock Reconciliation": "Stock Reconciliation Item",
	"Subcontracting Receipt": "Subcontracting Receipt Item",
}


def execute():
	"""Move legacy inventory-dimension data onto the new quantity sub-ledger.

	Old dimensions stored their value as a column on every stock doctype + Stock Ledger Entry.
	The redesign keeps a single Link column per dimension on Inventory Dimension Entry and a
	single `inventory_dimension_bundle` link on the transaction rows + SLE. This patch:
	  1. adds the per-dimension column to Inventory Dimension Entry for each legacy dimension, and
	  2. reconstructs the sub-ledger from historical SLEs (one Inventory Dimension Bundle per
	     voucher row), stamping the bundle back onto the SLEs and the transaction rows.
	"""
	# Existing sites that already use Inventory Dimensions should keep the feature on after the
	# redesign (it is gated behind a Stock Settings switch that defaults to off for new sites).
	enable_inventory_dimension_feature()

	# SLE column == target fieldname; Entry column == source fieldname.
	legacy = [
		d for d in get_inventory_dimensions() if frappe.db.has_column("Stock Ledger Entry", d.fieldname)
	]
	if not legacy:
		return

	add_entry_columns(legacy)
	backfill_sub_ledger(legacy)


def enable_inventory_dimension_feature():
	"""Turn on the Stock Settings switch if any Inventory Dimension is already defined."""
	if not frappe.db.count("Inventory Dimension"):
		return

	if not frappe.db.get_single_value("Stock Settings", "enable_inventory_dimension"):
		frappe.db.set_single_value("Stock Settings", "enable_inventory_dimension", 1)


def add_entry_columns(legacy):
	created = False
	for dimension in legacy:
		if frappe.db.has_column("Inventory Dimension Entry", dimension.source_fieldname):
			continue
		frappe.get_doc("Inventory Dimension", dimension.dimension_name).add_dimension_field()
		created = True

	if created:
		frappe.clear_cache(doctype="Inventory Dimension Entry")


def backfill_sub_ledger(legacy):
	sle_cols = sorted({d.fieldname for d in legacy})
	source_by_sle_col = {d.fieldname: d.source_fieldname for d in legacy}

	sle = frappe.qb.DocType("Stock Ledger Entry")
	query = (
		frappe.qb.from_(sle)
		.select(
			sle.name,
			sle.item_code,
			sle.warehouse,
			sle.company,
			sle.voucher_type,
			sle.voucher_no,
			sle.voucher_detail_no,
			sle.actual_qty,
			sle.posting_datetime,
			*[sle[col] for col in sle_cols],
		)
		.where(sle.is_cancelled == 0)
		.where(sle.inventory_dimension_bundle.isnull() | (sle.inventory_dimension_bundle == ""))
		# at least one legacy dimension column is set on the SLE
		.where(Criterion.any([sle[col].isnotnull() & (sle[col] != "") for col in sle_cols]))
		.orderby(sle.voucher_type)
		.orderby(sle.voucher_no)
		.orderby(sle.voucher_detail_no)
		.orderby(sle.posting_datetime)
	)
	rows = query.run(as_dict=True)
	if not rows:
		return

	groups = {}
	for sle in rows:
		groups.setdefault((sle.voucher_type, sle.voucher_no, sle.voucher_detail_no), []).append(sle)

	# Rebuild bundles in chronological order so an inward receipt is always migrated before the
	# outward issue that draws it down (the SQL sort is by voucher_type/no, which is not chronological).
	ordered_groups = sorted(groups.items(), key=lambda group: group[1][0].posting_datetime)

	for (voucher_type, voucher_no, voucher_detail_no), entries in ordered_groups:
		first = entries[0]
		net_qty = sum(flt(e.actual_qty) for e in entries)

		bundle = frappe.new_doc("Inventory Dimension Bundle")
		bundle.company = first.company
		bundle.item_code = first.item_code
		bundle.warehouse = first.warehouse
		bundle.voucher_type = voucher_type
		bundle.voucher_no = voucher_no
		bundle.voucher_detail_no = voucher_detail_no
		bundle.posting_datetime = first.posting_datetime
		bundle.type_of_transaction = "Outward" if net_qty < 0 else "Inward"

		for sle in entries:
			row = {
				# qty is stored signed (negative for outward), matching the SLE's actual_qty.
				"qty": flt(sle.actual_qty),
				"is_outward": 1 if flt(sle.actual_qty) < 0 else 0,
				"warehouse": sle.warehouse,
				"posting_datetime": sle.posting_datetime,
			}
			for col in sle_cols:
				if sle.get(col):
					row[source_by_sle_col[col]] = sle.get(col)
			bundle.append("entries", row)

		bundle.flags.ignore_permissions = True
		bundle.insert()
		bundle.submit()

		for sle in entries:
			frappe.db.set_value(
				"Stock Ledger Entry",
				sle.name,
				"inventory_dimension_bundle",
				bundle.name,
				update_modified=False,
			)

		link_transaction_row(voucher_type, voucher_detail_no, bundle.name)


def link_transaction_row(voucher_type, voucher_detail_no, bundle):
	child_doctype = ITEM_TABLE.get(voucher_type)
	if not child_doctype or not voucher_detail_no:
		return
	if not frappe.db.has_column(child_doctype, "inventory_dimension_bundle"):
		return
	if frappe.db.exists(child_doctype, voucher_detail_no):
		frappe.db.set_value(
			child_doctype, voucher_detail_no, "inventory_dimension_bundle", bundle, update_modified=False
		)
