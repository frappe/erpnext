# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Quarantine actions: mint QC Lots when stock lands in a Quality (QC) warehouse.

This is deliberately route-agnostic — it reacts to a positive movement into a
Quality warehouse rather than re-resolving the trigger, so it works no matter how
the stock got there (receipt, transfer, redirect).
"""

import frappe

from erpnext.stock.services.quality_trigger_resolution import INBOUND, movements_of
from erpnext.stock.services.quality_warehouse import is_quality_warehouse


def create_qc_lots(doc, method=None):
	"""Mint a QC Lot for each item moving into a Quality warehouse on this document."""
	for row, role, warehouse in movements_of(doc):
		if role != INBOUND or not is_quality_warehouse(warehouse):
			continue

		received_qty = row.get("transfer_qty") or row.get("stock_qty") or row.get("qty")
		if not received_qty:
			continue

		frappe.get_doc(
			{
				"doctype": "QC Lot",
				"item_code": row.get("item_code"),
				"company": doc.get("company"),
				"quality_warehouse": warehouse,
				"batch_no": row.get("batch_no"),
				"received_qty": received_qty,
				"source_document_type": doc.doctype,
				"source_document": doc.name,
			}
		).insert(ignore_permissions=True)
