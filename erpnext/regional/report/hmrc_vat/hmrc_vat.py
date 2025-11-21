# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.utils import DocType
from frappe.types import DF

def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	vat_report = UKVatReport(filters)
	return vat_report.run()


class UKVatReport:
	def __init__(self, filters=None):
		self.company = filters.get("company")
		self.from_date = filters.get("from_date")
		self.to_date = filters.get("to_date")

	def run(self):
		columns = get_columns()
		data = self.get_data()
		return columns, data

	def get_data(self) -> list[list]:
		"""Return data for the report.

		The report data is a list of rows, with each row being a list of cell values.
		"""
		data = []
		doctype_party = [("Sales Invoice", "Customer"), ("Purchase Invoice", "Supplier")]
		for doctype, party in doctype_party:
			invoices = self.get_invoices(doctype, party)
			invoice_items = self.get_invoice_items(doctype, invoices)
			data.extend(invoices)
		return data

	def get_invoices(
			self,
			invoice_type: DF.Literal["Sales Invoice", "Purchase Invoice"],
			party_type: DF.Literal["Customer", "Supplier"]
		) -> list[dict]:
		dt = DocType(invoice_type)
		result = (
			frappe.qb.from_(dt)
			.select(
				ConstantColumn(invoice_type).as_("invoice_type"),
				ConstantColumn(party_type).as_("party_type"),
				dt.name.as_("invoice"),
				getattr(dt, party_type.lower()).as_("party"),
				dt.posting_date.as_("posting_date"),
				dt.grand_total.as_("invoice_amount"),
				dt.total_taxes_and_charges.as_("tax_total")
			)
			.where(dt.docstatus == 1)
			.where(dt.company == self.company)
			.where(dt.posting_date[self.from_date:self.to_date])
		).run()
  
		return result

	def get_invoice_items(
			self,
			invoice_type: DF.Literal["Sales Invoice", "Purchase Invoice"],
			invoices: list[dict]
		):
		Item = DocType(invoice_type + " Item")
		invoices = [invoice["invoice"] for invoice in invoices]
		invoice_items = (
			frappe.qb.from_(Item)
			.select(
				Item.item_code,
				Item.parent.as_("invoice"),
				Item.base_net_amount.as_("item_amount"),
				Item.item_tax_template.as_("item_tax_template")
			)
			.where(
				Item.parent.in_(invoices)
			)
		).run()
		return invoice_items


def get_columns() -> list[dict]:
	"""Return columns for the report.

	One field definition per column, just like a DocType field definition.
	"""
	return [
		{
			"label": _("Invoice Type"),
			"fieldname": "invoice_type",
			"fieldtype": "Link",
			"options": "DocType",
			"hidden": True,
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"fieldtype": "Link",
			"options": "DocType",
			"hidden": True,
		},
		{
			"label": _("Invoice"),
			"fieldname": "invoice",
			"fieldtype": "Dynamic Link",
			"options": "invoice_type"
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 120,
		},
		{
			"label": _("Posting Date"),
   			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 80
		},
		{
			"label": _("Invoice Amount"),
			"fieldname": "invoice_amount",
			"fieldtype": "Currency",
		},
		{
			"label": _("Tax Total"),
			"fieldname": "tax_total",
			"fieldtype": "Currency",
		},
	]

