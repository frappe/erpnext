# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder import Criterion
from frappe.query_builder.custom import ConstantColumn


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	"""Return columns for the report.

	One field definition per column, just like a DocType field definition.
	"""
	return [
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Link", "options": "DocType"},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
		},
	]


def get_data(filters) -> list[list]:
	"""Return data for the report.

	The report data is a list of rows, with each row being a list of cell values.
	"""
	active_vouchers = get_active_vouchers_for_period(filters)
	invalid_vouchers = identify_cancelled_vouchers(active_vouchers)

	return invalid_vouchers


def identify_cancelled_vouchers(active_vouchers: list[dict] | list | None = None) -> list[dict]:
	cancelled_vouchers = []
	if active_vouchers:
		# Group by voucher types and use single query to identify cancelled vouchers
		vtypes = set([x.voucher_type for x in active_vouchers])

		for _t in vtypes:
			_names = [x.voucher_no for x in active_vouchers if x.voucher_type == _t]
			dt = qb.DocType(_t)
			non_active_vouchers = (
				qb.from_(dt)
				.select(ConstantColumn(_t).as_("voucher_type"), dt.name.as_("voucher_no"))
				.where(dt.docstatus.ne(1) & dt.name.isin(_names))
				.run(as_dict=True)
			)
			if non_active_vouchers:
				cancelled_vouchers.extend(non_active_vouchers)
	return cancelled_vouchers


def validate_filters(filters: dict | None = None):
	if not filters:
		frappe.throw(_("Filters missing"))

	if not filters.company:
		frappe.throw(_("Company is mandatory"))

	if filters.from_date > filters.to_date:
		frappe.throw(_("Start Date should be lower than End Date"))


def build_query_filters(filters: dict | None = None) -> list:
	qb_filters = []
	if filters:
		if filters.account:
			qb_filters.append(qb.Field("account").isin(filters.account))

		if filters.voucher_no:
			qb_filters.append(qb.Field("voucher_no").eq(filters.voucher_no))

	return qb_filters


def get_active_vouchers_for_period(filters: dict | None = None) -> list[dict]:
	uniq_vouchers = []

	if filters:
		gle = qb.DocType("GL Entry")
		ple = qb.DocType("Payment Ledger Entry")

		qb_filters = build_query_filters(filters)

		gl_vouchers = (
			qb.from_(gle)
			.select(gle.voucher_type)
			.distinct()
			.select(gle.voucher_no)
			.distinct()
			.where(
				gle.is_cancelled.eq(0)
				& gle.company.eq(filters.company)
				& gle.posting_date[filters.from_date : filters.to_date]
			)
			.where(Criterion.all(qb_filters))
			.run(as_dict=True)
		)

		pl_vouchers = (
			qb.from_(ple)
			.select(ple.voucher_type)
			.distinct()
			.select(ple.voucher_no)
			.distinct()
			.where(
				ple.delinked.eq(0)
				& ple.company.eq(filters.company)
				& ple.posting_date[filters.from_date : filters.to_date]
			)
			.where(Criterion.all(qb_filters))
			.run(as_dict=True)
		)

		uniq_vouchers.extend(gl_vouchers)
		uniq_vouchers.extend(pl_vouchers)

	return uniq_vouchers
