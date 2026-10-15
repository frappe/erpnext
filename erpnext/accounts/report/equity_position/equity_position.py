# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Max, NullIf, Sum
from frappe.utils import cint, nowdate
from pypika.terms import Case

from erpnext.accounts.shareholding.report_permissions import apply_report_filters


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.as_of_date = filters.as_of_date or nowdate()
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{
			"fieldname": "share_class",
			"label": _("Share Class"),
			"fieldtype": "Link",
			"options": "Share Class",
			"width": 140,
		},
		{
			"fieldname": "share_folio",
			"label": _("Share Folio"),
			"fieldtype": "Link",
			"options": "Share Folio",
			"width": 130,
		},
		{"fieldname": "folio_number", "label": _("Folio Number"), "fieldtype": "Data", "width": 120},
		{
			"fieldname": "shareholder",
			"label": _("Shareholder"),
			"fieldtype": "Link",
			"options": "Shareholder",
			"width": 150,
		},
		{"fieldname": "holding_type", "label": _("Holding Type"), "fieldtype": "Data", "width": 105},
		{"fieldname": "quantity", "label": _("Current Shares"), "fieldtype": "Int", "width": 115},
		{
			"fieldname": "face_value_per_share",
			"label": _("Face Value"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"fieldname": "total_face_value",
			"label": _("Total Face Value"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 135,
		},
		{
			"fieldname": "treasury_cost",
			"label": _("Treasury Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 85,
		},
	]


def get_data(filters, *, ignore_company_permissions=False):
	entry = frappe.qb.DocType("Share Ledger Entry")
	folio = frappe.qb.DocType("Share Folio")
	quantity = Sum(entry.quantity_change)
	unknown_quantity = Sum(
		Case()
		.when(entry.face_value_per_share.isnull() | (entry.face_value_per_share <= 0), entry.quantity_change)
		.else_(0)
	)
	face_value = (
		Case()
		.when(unknown_quantity != 0, None)
		.else_(Sum(entry.quantity_change * entry.face_value_per_share))
	)
	query = (
		frappe.qb.from_(entry)
		.join(folio)
		.on(folio.name == entry.share_folio)
		.select(
			entry.company,
			entry.share_class,
			entry.share_folio,
			folio.folio_number,
			folio.shareholder,
			Case().when(folio.is_treasury == 1, "Treasury").else_("Shareholder").as_("holding_type"),
			quantity.as_("quantity"),
			(face_value / NullIf(quantity, 0)).as_("face_value_per_share"),
			face_value.as_("total_face_value"),
			Sum(entry.treasury_cost_change).as_("treasury_cost"),
			Max(entry.currency).as_("currency"),
		)
		.groupby(
			entry.company,
			entry.share_class,
			entry.share_folio,
			folio.folio_number,
			folio.shareholder,
			folio.is_treasury,
		)
	)
	query = apply_report_filters(
		query, entry, folio, filters, ignore_company_permissions=ignore_company_permissions
	)
	if not cint(filters.get("include_zero_positions")):
		query = query.having(quantity != 0)
	return query.orderby(entry.company, entry.share_class, folio.is_treasury, folio.folio_number).run(
		as_dict=True
	)
