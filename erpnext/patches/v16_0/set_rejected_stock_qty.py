import frappe
from frappe.utils import flt


def execute():
	for doctype in ("Purchase Receipt Item", "Purchase Invoice Item"):
		precision = frappe.get_precision(doctype, "rejected_stock_qty")
		rows = frappe.get_all(
			doctype,
			filters={"rejected_qty": ("!=", 0)},
			fields=["name", "rejected_qty", "conversion_factor"],
			limit_page_length=0,
		)
		frappe.db.bulk_update(
			doctype,
			{
				row.name: {
					"rejected_stock_qty": flt(flt(row.rejected_qty) * flt(row.conversion_factor), precision)
				}
				for row in rows
			},
			update_modified=False,
		)
