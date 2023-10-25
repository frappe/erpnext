import frappe
from frappe import _

from erpnext.accounts.report.tds_payable_monthly.tds_payable_monthly import (
	get_result,
	get_tds_docs,
)
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	if filters.get("party_type") == "Customer":
		party_naming_by = frappe.db.get_single_value("Selling Settings", "cust_master_name")
	else:
		party_naming_by = frappe.db.get_single_value("Buying Settings", "supp_master_name")

	filters.update({"naming_series": party_naming_by})

	validate_filters(filters)

	columns = get_columns(filters)
	(
		tds_docs,
		tds_accounts,
		tax_category_map,
		journal_entry_party_map,
		invoice_total_map,
	) = get_tds_docs(filters)

	res = get_result(
		filters, tds_docs, tds_accounts, tax_category_map, journal_entry_party_map, invoice_total_map
	)
	final_result = group_by_party_and_category(res, filters)

	return columns, final_result


def validate_filters(filters):
	"""Validate if dates are properly set and lie in the same fiscal year"""
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	from_year = get_fiscal_year(filters.from_date)[0]
	to_year = get_fiscal_year(filters.to_date)[0]
	if from_year != to_year:
		frappe.throw(_("From Date and To Date lie in different Fiscal Year"))

	filters["fiscal_year"] = from_year


def group_by_party_and_category(data, filters):
	party_category_wise_map = {}

	for row in data:
		party_category_wise_map.setdefault(
			(row.get("party"), row.get("section_code")),
			{
				"pan": row.get("pan"),
				"tax_id": row.get("tax_id"),
				"party": row.get("party"),
				"party_name": row.get("party_name"),
				"section_code": row.get("section_code"),
				"entity_type": row.get("entity_type"),
				"rate": row.get("rate"),
				"total_amount": 0.0,
				"tax_amount": 0.0,
			},
		)

		party_category_wise_map.get((row.get("party"), row.get("section_code")))[
			"total_amount"
		] += row.get("total_amount", 0.0)

		party_category_wise_map.get((row.get("party"), row.get("section_code")))[
			"tax_amount"
		] += row.get("tax_amount", 0.0)

	final_result = get_final_result(party_category_wise_map)

	return final_result


def get_final_result(party_category_wise_map):
	out = []
	for key, value in party_category_wise_map.items():
		out.append(value)

	return out


def get_columns(filters):
	pan = "pan" if frappe.db.has_column(filters.party_type, "pan") else "tax_id"
	columns = [
		{"label": _(frappe.unscrub(pan)), "fieldname": pan, "fieldtype": "Data", "width": 90},
		{
			"label": _(filters.get("party_type")),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 180,
		},
	]

	if filters.naming_series == "Naming Series":
		columns.append(
			{
				"label": _(filters.party_type + " Name"),
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 180,
			}
		)

	columns.extend(
		[
			{
				"label": _("Section Code"),
				"options": "Tax Withholding Category",
				"fieldname": "section_code",
				"fieldtype": "Link",
				"width": 180,
			},
			{"label": _("Entity Type"), "fieldname": "entity_type", "fieldtype": "Data", "width": 180},
			{
				"label": _("TDS Rate %") if filters.get("party_type") == "Supplier" else _("TCS Rate %"),
				"fieldname": "rate",
				"fieldtype": "Percent",
				"width": 120,
			},
			{
				"label": _("Total Amount"),
				"fieldname": "total_amount",
				"fieldtype": "Float",
				"width": 120,
			},
			{
				"label": _("Tax Amount"),
				"fieldname": "tax_amount",
				"fieldtype": "Float",
				"width": 120,
			},
		]
	)

	return columns
