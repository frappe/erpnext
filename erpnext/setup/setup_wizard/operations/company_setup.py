# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import cstr, getdate


def create_fiscal_year_and_company(args):
	if args.get("fy_start_date"):
		curr_fiscal_year = get_fy_details(args.get("fy_start_date"), args.get("fy_end_date"))
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": curr_fiscal_year,
				"year_start_date": args.get("fy_start_date"),
				"year_end_date": args.get("fy_end_date"),
			}
		).insert()

	if args.get("company_name"):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": args.get("company_name"),
				"enable_perpetual_inventory": 1,
				"abbr": args.get("company_abbr"),
				"default_currency": args.get("currency"),
				"country": args.get("country"),
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": args.get("chart_of_accounts"),
			}
		).insert()


def enable_shopping_cart(args):  # nosemgrep
	# Needs price_lists
	frappe.get_doc(
		{
			"doctype": "E Commerce Settings",
			"enabled": 1,
			"company": args.get("company_name"),
			"price_list": frappe.db.get_value("Price List", {"selling": 1}),
			"default_customer_group": _("Individual"),
			"quotation_series": "QTN-",
		}
	).insert()


def get_fy_details(fy_start_date, fy_end_date):
	start_year = getdate(fy_start_date).year
	if start_year == getdate(fy_end_date).year:
		fy = cstr(start_year)
	else:
		fy = cstr(start_year) + "-" + cstr(start_year + 1)
	return fy
