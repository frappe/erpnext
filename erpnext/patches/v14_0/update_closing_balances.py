# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE


import frappe

from erpnext.accounts.doctype.account_closing_balance.account_closing_balance import (
	make_closing_entries,
)
from erpnext.accounts.utils import get_fiscal_year


def execute():
	frappe.db.truncate("Account Closing Balance")

	for company in frappe.get_all("Company", pluck="name"):
		i = 0
		company_wise_order = {}
		for pcv in frappe.db.get_all(
			"Period Closing Voucher",
			fields=["company", "posting_date", "name"],
			filters={"docstatus": 1, "company": company},
			order_by="posting_date",
		):

			company_wise_order.setdefault(pcv.company, [])
			if pcv.posting_date not in company_wise_order[pcv.company]:
				pcv_doc = frappe.get_doc("Period Closing Voucher", pcv.name)
				pcv_doc.year_start_date = get_fiscal_year(
					pcv.posting_date, pcv.fiscal_year, company=pcv.company
				)[1]

				# get gl entries against pcv
				gl_entries = frappe.db.get_all(
					"GL Entry", filters={"voucher_no": pcv.name, "is_cancelled": 0}, fields=["*"]
				)
				for entry in gl_entries:
					entry["is_period_closing_voucher_entry"] = 1
					entry["closing_date"] = pcv_doc.posting_date
					entry["period_closing_voucher"] = pcv_doc.name

				closing_entries = []

				if pcv.posting_date not in company_wise_order[pcv.company]:
					# get all gl entries for the year
					closing_entries = frappe.db.get_all(
						"GL Entry",
						filters={
							"is_cancelled": 0,
							"voucher_no": ["!=", pcv.name],
							"posting_date": ["between", [pcv_doc.year_start_date, pcv.posting_date]],
							"is_opening": "No",
							"company": company,
						},
						fields=["*"],
					)

				if i == 0:
					# add opening entries only for the first pcv
					closing_entries += frappe.db.get_all(
						"GL Entry",
						filters={"is_cancelled": 0, "is_opening": "Yes", "company": company},
						fields=["*"],
					)

				for entry in closing_entries:
					entry["closing_date"] = pcv_doc.posting_date
					entry["period_closing_voucher"] = pcv_doc.name

				entries = gl_entries + closing_entries

				make_closing_entries(entries, pcv.name, pcv.company, pcv.posting_date)
				company_wise_order[pcv.company].append(pcv.posting_date)
				i += 1
