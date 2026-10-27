# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import qb
from frappe.utils import flt

from erpnext.projects.doctype.project.costing.queries import (
	ProjectCostQueries,
	combine,
	sum_amount,
	sum_by,
)
from erpnext.projects.doctype.project.project_overview_unbilled import get_unbilled_time


class ProjectBilling:
	"""How a project is billed: its sales orders, the invoices billed to it, and what is left to bill.

	The amounts that sum up the project show to every user who can read it; the orders and invoices
	behind them only to users who can read those doctypes.
	"""

	def __init__(self, project: str, access: dict[str, bool], currency: str, contract: float, billed: float):
		self.project = project
		self.queries = ProjectCostQueries(project)
		self.access = access
		self.currency = currency
		self.contract = flt(contract)
		self.billed = flt(billed)

	def build(self) -> dict:
		invoices = self.invoices()
		closed_remainder = self.closed_order_remainder()
		left_to_bill = self.contract - self.billed - closed_remainder
		return {
			"sales_orders": self.sales_orders(),
			"invoices": invoices,
			"outstanding": sum(invoice["outstanding"] for invoice in invoices)
			if invoices is not None
			else None,
			"closed_remainder": closed_remainder,
			"left_to_bill": max(left_to_bill, 0) if self.contract else None,
			"over_billed": bool(self.contract) and self.billed > self.contract,
			# timesheet billing amounts show to the users who can see costing rates
			"unbilled": get_unbilled_time(self.project) if self.access["labour"] else None,
		}

	def sales_orders(self) -> list[dict] | None:
		if not self.access["sales_orders"]:
			return None
		return frappe.get_list(
			"Sales Order",
			filters={"project": self.project, "docstatus": 1},
			fields=["name", "transaction_date", "status", "base_net_total", "per_billed"],
			order_by="transaction_date asc",
		)

	def invoices(self) -> list[dict] | None:
		"""Invoices billed to the project that the user may read, newest first, each with the amount
		it bills to this project. Outstanding is the whole invoice's, in the company's currency."""
		if not self.access["invoices"]:
			return None
		amounts = self.billed_by_invoice()
		if not amounts:
			return []
		invoices = frappe.get_list(
			"Sales Invoice",
			filters={"name": ["in", list(amounts)]},
			fields=[
				"name",
				"posting_date",
				"status",
				"outstanding_amount",
				"party_account_currency",
				"conversion_rate",
			],
			order_by="posting_date desc",
		)
		return [self.invoice_row(invoice, amounts[invoice.name]) for invoice in invoices]

	def invoice_row(self, invoice: frappe._dict, amount: float) -> dict:
		return {
			"name": invoice.name,
			"posting_date": invoice.posting_date,
			"status": invoice.status,
			"amount": amount,
			"outstanding": self.outstanding_in_company_currency(invoice),
		}

	def billed_by_invoice(self) -> dict[str, float]:
		invoice = qb.DocType("Sales Invoice")
		item = qb.DocType("Sales Invoice Item")
		from_invoice, from_item = self.queries.billed_items()
		return combine(
			sum_by(from_invoice, invoice.name, item.base_net_amount),
			sum_by(from_item, invoice.name, item.base_net_amount),
		)

	def outstanding_in_company_currency(self, invoice: frappe._dict) -> float:
		"""An invoice owes in its party account's currency, which can differ from the company's."""
		if invoice.party_account_currency == self.currency:
			return flt(invoice.outstanding_amount)
		return flt(invoice.outstanding_amount) * flt(invoice.conversion_rate)

	def closed_order_remainder(self) -> float:
		"""The unbilled part of closed sales orders, which will not be billed."""
		order = qb.DocType("Sales Order")
		unbilled = order.base_net_total * (100 - order.per_billed) / 100
		query = qb.from_(order).where(
			(order.project == self.project) & (order.docstatus == 1) & (order.status == "Closed")
		)
		return sum_amount(query, unbilled)
