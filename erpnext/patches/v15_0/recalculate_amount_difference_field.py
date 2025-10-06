import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import adjust_incoming_rate_for_pr


def execute():
	if not frappe.db.get_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate"):
		return

	for company in frappe.get_all("Company", pluck="name"):
		table = frappe.qb.DocType("Purchase Receipt Item")
		parent = frappe.qb.DocType("Purchase Receipt")
		query = (
			frappe.qb.from_(table)
			.join(parent)
			.on(table.parent == parent.name)
			.select(
				table.parent,
				table.name,
				table.amount,
				table.billed_amt,
				table.amount_difference_with_purchase_invoice,
				table.rate,
				table.qty,
				parent.conversion_rate,
			)
			.where((table.docstatus == 1) & (parent.company == company))
		)

		posting_date = "2024-04-01"

		# Get the last accounting period end date
		accounting_period = frappe.get_all(
			"Accounting Period", {"company": company}, ["end_date"], order_by="end_date desc", limit=1
		)
		if (
			accounting_period
			and accounting_period[0].end_date
			and getdate(accounting_period[0].end_date) > getdate(posting_date)
		):
			posting_date = accounting_period[0].end_date

		# Get the last period closing voucher end date
		period_closing_voucher = frappe.get_all(
			"Period Closing Voucher",
			{"company": company, "docstatus": 1},
			["period_end_date"],
			order_by="period_end_date desc",
			limit=1,
		)
		if (
			period_closing_voucher
			and period_closing_voucher[0].period_end_date
			and getdate(period_closing_voucher[0].period_end_date) > getdate(posting_date)
		):
			posting_date = period_closing_voucher[0].period_end_date

		acc_frozen_upto = frappe.db.get_single_value("Accounts Settings", "acc_frozen_upto")
		if acc_frozen_upto and getdate(acc_frozen_upto) > getdate(posting_date):
			posting_date = acc_frozen_upto

		stock_frozen_upto = frappe.db.get_single_value("Stock Settings", "stock_frozen_upto")
		if stock_frozen_upto and getdate(stock_frozen_upto) > getdate(posting_date):
			posting_date = stock_frozen_upto

		fiscal_year = get_fiscal_year(frappe.utils.datetime.date.today(), raise_on_missing=False)
		if fiscal_year and getdate(fiscal_year[1]) > getdate(posting_date):
			posting_date = fiscal_year[1]
		query = query.where(parent.posting_date > posting_date)

		if result := query.run(as_dict=True):
			item_wise_billed_qty = get_billed_qty_against_purchase_receipt([item.name for item in result])

			purchase_receipts = set()
			precision = frappe.get_precision("Purchase Receipt Item", "amount")
			for item in result:
				adjusted_amt = 0.0

				if (
					item.billed_amt is not None
					and item.amount is not None
					and item_wise_billed_qty.get(item.name)
				):
					adjusted_amt = (
						flt(item.billed_amt / item_wise_billed_qty.get(item.name)) - flt(item.rate)
					) * item.qty
				adjusted_amt = flt(
					adjusted_amt * flt(item.conversion_rate),
					precision,
				)

				if adjusted_amt != item.amount_difference_with_purchase_invoice:
					frappe.db.set_value(
						"Purchase Receipt Item",
						item.name,
						"amount_difference_with_purchase_invoice",
						adjusted_amt,
						update_modified=False,
					)
					purchase_receipts.add(item.parent)

			for pr in purchase_receipts:
				adjust_incoming_rate_for_pr(frappe.get_doc("Purchase Receipt", pr))


def get_billed_qty_against_purchase_receipt(pr_names):
	table = frappe.qb.DocType("Purchase Invoice Item")
	query = (
		frappe.qb.from_(table)
		.select(table.pr_detail, Sum(table.qty).as_("qty"))
		.where((table.pr_detail.isin(pr_names)) & (table.docstatus == 1))
		.groupby(table.pr_detail)
	)
	invoice_data = query.run(as_list=1)

	if not invoice_data:
		return frappe._dict()
	return frappe._dict(invoice_data)
