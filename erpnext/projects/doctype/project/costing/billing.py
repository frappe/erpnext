# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import qb

from erpnext.projects.doctype.project.costing.queries import ProjectCostQueries, combine, sum_by

# Orders and invoices the Billing card lists, newest first; it links to the rest.
LIST_LIMIT = 5
# Invoices the Billing card loads at a time when no list filter finds them all.
INVOICE_PAGE = 20


class ProjectBilling:
	"""How a project is billed: the sales orders and invoices for it, newest first.

	The orders and invoices show only to users who can read those doctypes.
	"""

	def __init__(self, project: str, access: dict[str, bool]):
		self.project = project
		self.queries = ProjectCostQueries(project)
		self.access = access
		# orders and invoices whose items name the project, set while the amounts are worked out
		self.item_ordered_orders = set()
		self.item_billed_invoices = set()

	def build(self) -> dict:
		orders = self.sales_orders()
		invoices = self.invoices()
		order_filter = self.order_filter(orders) if orders else None
		# the card links to the rest through the filter; without one, it lists every order
		listed_orders = orders[:LIST_LIMIT] if order_filter else orders
		return {
			"sales_orders": listed_orders,
			"sales_order_count": len(orders) if orders is not None else None,
			"order_filter": order_filter,
			"invoices": invoices and invoices[:LIST_LIMIT],
			"invoice_count": len(invoices) if invoices is not None else None,
			"invoice_filter": self.invoice_filter(invoices) if invoices else None,
		}

	def sales_orders(self) -> list[dict] | None:
		"""Orders for the project that the user may read, newest first, each with the amount it adds
		to this project's contract."""
		if not self.access["sales_orders"]:
			return None
		amounts = self.ordered_by_order()
		if not amounts:
			return []
		orders = frappe.get_list(
			"Sales Order",
			filters={"name": ["in", list(amounts)]},
			fields=["name", "transaction_date", "status", "base_net_total", "per_billed", "project"],
			order_by="transaction_date desc, name desc",
		)
		return [{**order, "amount": amounts[order.name]} for order in orders]

	def invoices(self, start: int = 0, page_length: int | None = None) -> list[dict] | None:
		"""Invoices billed to the project that the user may read, newest first, each with the amount
		it bills to this project: all of them, or the page from `start` when `page_length` is given."""
		if not self.access["invoices"]:
			return None
		amounts = self.billed_by_invoice()
		if not amounts:
			return []
		invoices = frappe.get_list(
			"Sales Invoice",
			filters={"name": ["in", list(amounts)]},
			fields=["name", "posting_date", "status", "project"],
			# by name too, so pages of invoices dated the same day neither repeat nor skip one
			order_by="posting_date desc, name desc",
			offset=start,
			limit=page_length,
		)
		return [{**invoice, "amount": amounts[invoice.name]} for invoice in invoices]

	def invoice_filter(self, invoices: list[dict]) -> dict | None:
		"""The Sales Invoice list filter that finds the invoices counted here. An invoice can name the
		project on itself or only on its items, and the list cannot match either at once. None for
		a mix of the two: the Billing card then pages through them with `get_project_invoices`."""
		if all(invoice["project"] == self.project for invoice in invoices):
			return {"project": self.project}
		if {invoice["name"] for invoice in invoices} <= self.item_billed_invoices:
			return {"Sales Invoice Item.project": self.project}
		return None

	def order_filter(self, orders: list[dict]) -> dict | None:
		"""The Sales Order list filter that finds the orders counted here, as `invoice_filter` does
		for invoices. None for a mix of orders that name the project on themselves and on items."""
		if all(order["project"] == self.project for order in orders):
			return {"project": self.project}
		if {order["name"] for order in orders} <= self.item_ordered_orders:
			return {"Sales Order Item.project": self.project}
		return None

	def ordered_by_order(self) -> dict[str, float]:
		order = qb.DocType("Sales Order")
		item = qb.DocType("Sales Order Item")
		from_order, from_item = self.queries.ordered_items()
		from_items = sum_by(from_item, order.name, item.base_net_amount)
		self.item_ordered_orders = set(from_items)
		return combine(sum_by(from_order, order.name, item.base_net_amount), from_items)

	def billed_by_invoice(self) -> dict[str, float]:
		invoice = qb.DocType("Sales Invoice")
		item = qb.DocType("Sales Invoice Item")
		from_invoice, from_item = self.queries.billed_items()
		from_items = sum_by(from_item, invoice.name, item.base_net_amount)
		self.item_billed_invoices = set(from_items)
		return combine(sum_by(from_invoice, invoice.name, item.base_net_amount), from_items)
