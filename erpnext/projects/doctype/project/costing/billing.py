# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import qb

from erpnext.projects.doctype.project.costing.queries import ProjectCostQueries, combine, sum_by

# Orders and invoices the Billing card lists, newest first; it links to the rest.
LIST_LIMIT = 5


class ProjectBilling:
	"""How a project is billed: its sales orders and the invoices billed to it, newest first.

	The orders and invoices show only to users who can read those doctypes.
	"""

	def __init__(self, project: str, access: dict[str, bool]):
		self.project = project
		self.queries = ProjectCostQueries(project)
		self.access = access
		# invoices whose items name the project, set while the amounts are worked out
		self.item_billed_invoices = set()

	def build(self) -> dict:
		orders = self.sales_orders()
		invoices = self.invoices()
		return {
			"sales_orders": orders and orders[:LIST_LIMIT],
			"sales_order_count": len(orders) if orders is not None else None,
			"invoices": invoices and invoices[:LIST_LIMIT],
			"invoice_count": len(invoices) if invoices is not None else None,
			"invoice_filter": self.invoice_filter(invoices) if invoices else None,
		}

	def sales_orders(self) -> list[dict] | None:
		if not self.access["sales_orders"]:
			return None
		return frappe.get_list(
			"Sales Order",
			filters={"project": self.project, "docstatus": 1},
			fields=["name", "transaction_date", "status", "base_net_total", "per_billed"],
			order_by="transaction_date desc",
		)

	def invoices(self) -> list[dict] | None:
		"""Invoices billed to the project that the user may read, newest first, each with the amount
		it bills to this project."""
		if not self.access["invoices"]:
			return None
		amounts = self.billed_by_invoice()
		if not amounts:
			return []
		invoices = frappe.get_list(
			"Sales Invoice",
			filters={"name": ["in", list(amounts)]},
			fields=["name", "posting_date", "status", "project"],
			order_by="posting_date desc",
		)
		return [{**invoice, "amount": amounts[invoice.name]} for invoice in invoices]

	def invoice_filter(self, invoices: list[dict]) -> dict:
		"""The Sales Invoice list filter that finds the invoices counted here. An invoice can name the
		project on itself or only on its items, and the list cannot match either at once, so a mix
		of the two is matched by name."""
		if all(invoice["project"] == self.project for invoice in invoices):
			return {"project": self.project}
		names = [invoice["name"] for invoice in invoices]
		if set(names) <= self.item_billed_invoices:
			return {"Sales Invoice Item.project": self.project}
		return {"name": ["in", names]}

	def billed_by_invoice(self) -> dict[str, float]:
		invoice = qb.DocType("Sales Invoice")
		item = qb.DocType("Sales Invoice Item")
		from_invoice, from_item = self.queries.billed_items()
		from_items = sum_by(from_item, invoice.name, item.base_net_amount)
		self.item_billed_invoices = set(from_items)
		return combine(sum_by(from_invoice, invoice.name, item.base_net_amount), from_items)
