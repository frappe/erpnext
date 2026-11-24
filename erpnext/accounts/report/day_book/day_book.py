# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.desk.reportview import build_match_conditions
from frappe.query_builder.functions import IfNull, Max, Min, Sum
from frappe.utils import flt, getdate
from pypika.terms import Bracket, LiteralValue

from erpnext.accounts.report.general_ledger.general_ledger import get_party_name_map


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	return get_columns(filters), get_data(filters)


def validate_filters(filters):
	if not filters.company:
		frappe.throw(_("{0} is mandatory").format(_("Company")))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date must be before To Date"))


def get_data(filters):
	legs = get_legs(filters)
	if not legs:
		return []

	party_names = get_party_name_map()
	vouchers = {}
	for leg in legs:
		key = (leg.voucher_type, leg.voucher_no)
		vouchers.setdefault(key, []).append(leg)

	data = []
	precision = frappe.get_precision("GL Entry", "debit")
	for (voucher_type, voucher_no), voucher_legs in vouchers.items():
		for leg in voucher_legs:
			leg.balance = flt(leg.debit - leg.credit, precision)
			leg.particulars = party_names.get(leg.party_type, {}).get(leg.party) or leg.party or leg.account

		main = get_main_leg(voucher_legs)
		key = f"{voucher_type}::{voucher_no}"
		data.append(
			{
				"voucher": key,
				"indent": 0,
				"posting_date": main.posting_date,
				"particulars": main.particulars,
				"voucher_type": voucher_type,
				"voucher_no": voucher_no,
				"debit": main.balance if main.balance > 0 else None,
				"credit": -main.balance if main.balance < 0 else None,
				"remarks": main.remarks,
			}
		)
		for idx, leg in enumerate(voucher_legs if filters.detailed else []):
			if not leg.balance:
				continue
			data.append(
				{
					"voucher": f"{key}::{idx}",
					"parent_voucher": key,
					"indent": 1,
					"particulars": leg.particulars,
					"account": leg.account,
					"debit": leg.balance if leg.balance > 0 else None,
					"credit": -leg.balance if leg.balance < 0 else None,
				}
			)

	return data


def get_main_leg(legs):
	with_party = [leg for leg in legs if leg.party]
	candidates = with_party or [leg for leg in legs if leg.balance > 0] or legs
	return max(candidates, key=lambda leg: abs(leg.balance))


def get_legs(filters):
	gle = qb.DocType("GL Entry")
	company_fb = frappe.get_cached_value("Company", filters.company, "default_finance_book")

	query = (
		qb.from_(gle)
		.select(
			gle.voucher_type,
			gle.voucher_no,
			gle.account,
			gle.party_type,
			gle.party,
			Min(gle.posting_date).as_("posting_date"),
			Sum(gle.debit).as_("debit"),
			Sum(gle.credit).as_("credit"),
			Max(gle.remarks).as_("remarks"),
			Min(gle.creation).as_("created"),
		)
		.where(gle.company == filters.company)
		.where(gle.is_cancelled == 0)
		.where(gle.posting_date[getdate(filters.from_date) : getdate(filters.to_date)])
		.where(IfNull(gle.finance_book, "").isin(["", company_fb or ""]))
		.groupby(gle.voucher_type, gle.voucher_no, gle.account, gle.party_type, gle.party)
		.orderby(Min(gle.posting_date))
		.orderby(Min(gle.creation))
	)

	if filters.voucher_type:
		query = query.where(gle.voucher_type == filters.voucher_type)

	if match_conditions := build_match_conditions("GL Entry"):
		query = query.where(Bracket(LiteralValue(match_conditions)))

	return query.run(as_dict=True)


def get_columns(filters):
	columns = [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Particulars"), "fieldname": "particulars", "fieldtype": "Data", "width": 260},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 140,
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 200,
		},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 140},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 140},
	]
	if filters.show_remarks:
		columns.append({"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 300})
	return columns
