# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, qb
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Abs, Sum
from frappe.utils import cint, flt, getdate

from erpnext.controllers.accounts_controller import validate_account_head


class TaxWithholdingCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.tax_withholding_account.tax_withholding_account import (
			TaxWithholdingAccount,
		)
		from erpnext.accounts.doctype.tax_withholding_rate.tax_withholding_rate import TaxWithholdingRate

		accounts: DF.Table[TaxWithholdingAccount]
		category_name: DF.Data | None
		consider_party_ledger_amount: DF.Check
		rates: DF.Table[TaxWithholdingRate]
		round_off_tax_amount: DF.Check
		tax_on_excess_amount: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_dates()
		self.validate_companies_and_accounts()
		self.validate_thresholds()

	def validate_dates(self):
		last_to_date = None
		rates = sorted(self.get("rates"), key=lambda d: getdate(d.from_date))

		for d in rates:
			if getdate(d.from_date) >= getdate(d.to_date):
				frappe.throw(_("Row #{0}: From Date cannot be before To Date").format(d.idx))

			# validate overlapping of dates
			if last_to_date and getdate(d.from_date) < getdate(last_to_date):
				frappe.throw(_("Row #{0}: Dates overlapping with other row").format(d.idx))

			last_to_date = d.to_date

	def validate_companies_and_accounts(self):
		existing_accounts = set()
		companies = set()
		for d in self.get("accounts"):
			# validate duplicate company
			if d.get("company") in companies:
				frappe.throw(_("Company {0} added multiple times").format(frappe.bold(d.get("company"))))
			companies.add(d.get("company"))

			# validate duplicate account
			if d.get("account") in existing_accounts:
				frappe.throw(_("Account {0} added multiple times").format(frappe.bold(d.get("account"))))

			validate_account_head(d.idx, d.get("account"), d.get("company"))
			existing_accounts.add(d.get("account"))

	def validate_thresholds(self):
		for d in self.get("rates"):
			if d.cumulative_threshold and d.single_threshold and d.cumulative_threshold < d.single_threshold:
				frappe.throw(
					_(
						"Row #{0}: Cumulative threshold cannot be less than Single Transaction threshold"
					).format(d.idx)
				)


def get_party_details(inv):
	party_type, party = "", ""

	if inv.doctype == "Sales Invoice":
		party_type = "Customer"
		party = inv.customer
	elif inv.doctype == "Journal Entry":
		party_type = inv.party_type
		party = inv.party
	else:
		party_type = "Supplier"
		party = inv.supplier

	if not party:
		frappe.throw(_("Please select {0} first").format(party_type))

	return party_type, party


def get_party_tax_withholding_details(inv, tax_withholding_category=None):
	if inv.doctype == "Payment Entry":
		inv.tax_withholding_net_total = inv.net_total
		inv.base_tax_withholding_net_total = inv.net_total

	pan_no = ""
	parties = []
	party_type, party = get_party_details(inv)
	has_pan_field = frappe.get_meta(party_type).has_field("pan")

	if not tax_withholding_category:
		if has_pan_field:
			fields = ["tax_withholding_category", "pan"]
		else:
			fields = ["tax_withholding_category"]

		tax_withholding_details = frappe.db.get_value(party_type, party, fields, as_dict=1)

		tax_withholding_category = tax_withholding_details.get("tax_withholding_category")
		pan_no = tax_withholding_details.get("pan")

	if not tax_withholding_category:
		return

	# if tax_withholding_category passed as an argument but not pan_no
	if not pan_no and has_pan_field:
		pan_no = frappe.db.get_value(party_type, party, "pan")

	# Get others suppliers with the same PAN No
	if pan_no:
		parties = frappe.get_all(party_type, filters={"pan": pan_no}, pluck="name")

	if not parties:
		parties.append(party)

	posting_date = inv.get("posting_date") or inv.get("transaction_date")
	tax_details = get_tax_withholding_details(tax_withholding_category, posting_date, inv.company)

	if not tax_details:
		frappe.msgprint(
			_(
				"Skipping Tax Withholding Category {0} as there is no associated account set for Company {1} in it."
			).format(tax_withholding_category, inv.company)
		)
		if inv.doctype == "Purchase Invoice":
			return {}, [], {}
		return {}

	if party_type == "Customer" and not tax_details.cumulative_threshold:
		# TCS is only chargeable on sum of invoiced value
		frappe.throw(
			_(
				"Tax Withholding Category {} against Company {} for Customer {} should have Cumulative Threshold value."
			).format(tax_withholding_category, inv.company, party)
		)

	tax_amount, tax_deducted, tax_deducted_on_advances, voucher_wise_amount = get_tax_amount(
		party_type, parties, inv, tax_details, posting_date, pan_no
	)

	if party_type == "Supplier" or inv.doctype == "Journal Entry":
		tax_row = get_tax_row_for_tds(tax_details, tax_amount)
	else:
		tax_row = get_tax_row_for_tcs(inv, tax_details, tax_amount, tax_deducted)

	cost_center = get_cost_center(inv)
	tax_row.update(
		{
			"cost_center": cost_center,
			"is_tax_withholding_account": 1,
		}
	)

	if cint(tax_details.round_off_tax_amount):
		inv.round_off_applicable_accounts_for_tax_withholding = tax_details.account_head

	if inv.doctype == "Purchase Invoice":
		return tax_row, tax_deducted_on_advances, voucher_wise_amount
	else:
		return tax_row


def get_cost_center(inv):
	cost_center = frappe.get_cached_value("Company", inv.company, "cost_center")

	if len(inv.get("taxes", [])) > 0:
		cost_center = inv.get("taxes")[0].cost_center

	return cost_center


def get_tax_withholding_details(tax_withholding_category, posting_date, company):
	tax_withholding = frappe.get_doc("Tax Withholding Category", tax_withholding_category)

	tax_rate_detail = get_tax_withholding_rates(tax_withholding, posting_date)

	for account_detail in tax_withholding.accounts:
		if company == account_detail.company:
			return frappe._dict(
				{
					"tax_withholding_category": tax_withholding_category,
					"account_head": account_detail.account,
					"rate": tax_rate_detail.tax_withholding_rate,
					"from_date": tax_rate_detail.from_date,
					"to_date": tax_rate_detail.to_date,
					"threshold": tax_rate_detail.single_threshold,
					"cumulative_threshold": tax_rate_detail.cumulative_threshold,
					"description": tax_withholding.category_name
					if tax_withholding.category_name
					else tax_withholding_category,
					"consider_party_ledger_amount": tax_withholding.consider_party_ledger_amount,
					"tax_on_excess_amount": tax_withholding.tax_on_excess_amount,
					"round_off_tax_amount": tax_withholding.round_off_tax_amount,
				}
			)


def get_tax_withholding_rates(tax_withholding, posting_date):
	# returns the row that matches with the fiscal year from posting date
	for rate in tax_withholding.rates:
		if getdate(rate.from_date) <= getdate(posting_date) <= getdate(rate.to_date):
			return rate

	frappe.throw(_("No Tax Withholding data found for the current posting date."))


def get_tax_row_for_tcs(inv, tax_details, tax_amount, tax_deducted):
	row = {
		"category": "Total",
		"charge_type": "Actual",
		"tax_amount": tax_amount,
		"description": tax_details.description,
		"account_head": tax_details.account_head,
	}

	if tax_deducted:
		# TCS already deducted on previous invoices
		# So, TCS will be calculated by 'Previous Row Total'

		taxes_excluding_tcs = [d for d in inv.taxes if d.account_head != tax_details.account_head]
		if taxes_excluding_tcs:
			# chargeable amount is the total amount after other charges are applied
			row.update(
				{
					"charge_type": "On Previous Row Total",
					"row_id": len(taxes_excluding_tcs),
					"rate": tax_details.rate,
				}
			)
		else:
			# if only TCS is to be charged, then net total is chargeable amount
			row.update({"charge_type": "On Net Total", "rate": tax_details.rate})

	return row


def get_tax_row_for_tds(tax_details, tax_amount):
	return {
		"category": "Total",
		"charge_type": "Actual",
		"tax_amount": tax_amount,
		"add_deduct_tax": "Deduct",
		"description": tax_details.description,
		"account_head": tax_details.account_head,
	}


def get_lower_deduction_certificate(company, posting_date, tax_details, pan_no):
	ldc_name = frappe.db.get_value(
		"Lower Deduction Certificate",
		{
			"pan_no": pan_no,
			"tax_withholding_category": tax_details.tax_withholding_category,
			"valid_from": ("<=", posting_date),
			"valid_upto": (">=", posting_date),
			"company": company,
		},
		"name",
	)

	if ldc_name:
		return frappe.get_doc("Lower Deduction Certificate", ldc_name)


def get_tax_amount(party_type, parties, inv, tax_details, posting_date, pan_no=None):
	vouchers, voucher_wise_amount = get_invoice_vouchers(
		parties,
		tax_details,
		inv.company,
		party_type=party_type,
	)

	payment_entry_vouchers = get_payment_entry_vouchers(
		parties, tax_details, inv.company, party_type=party_type
	)

	advance_vouchers = get_advance_vouchers(
		parties,
		company=inv.company,
		from_date=tax_details.from_date,
		to_date=tax_details.to_date,
		party_type=party_type,
	)

	taxable_vouchers = vouchers + advance_vouchers + payment_entry_vouchers
	tax_deducted_on_advances = 0

	if inv.doctype == "Purchase Invoice":
		tax_deducted_on_advances = get_taxes_deducted_on_advances_allocated(inv, tax_details)

	tax_deducted = 0
	if taxable_vouchers:
		tax_deducted = get_deducted_tax(taxable_vouchers, tax_details)

	# If advance is outside the current tax withholding period (usually a fiscal year), `get_deducted_tax` won't fetch it.
	# updating `tax_deducted` with correct advance tax value (from current and previous previous withholding periods), will allow the
	# rest of the below logic to function properly
	# ---FY 2023-------------||---------------------FY 2024-----------------------||--
	# ---Advance-------------||---------Inv_1--------Inv_2------------------------||--
	if tax_deducted_on_advances:
		tax_deducted += get_advance_tax_across_fiscal_year(tax_deducted_on_advances, tax_details)

	tax_amount = 0

	if party_type == "Supplier":
		# if tds account is changed.
		if not tax_deducted:
			tax_deducted = is_tax_deducted_on_the_basis_of_inv(vouchers)

		ldc = get_lower_deduction_certificate(inv.company, posting_date, tax_details, pan_no)
		if tax_deducted:
			net_total = inv.tax_withholding_net_total
			if ldc:
				limit_consumed = get_limit_consumed(ldc, parties)
				if is_valid_certificate(ldc, posting_date, limit_consumed):
					tax_amount = get_lower_deduction_amount(
						net_total, limit_consumed, ldc.certificate_limit, ldc.rate, tax_details
					)
				else:
					tax_amount = net_total * tax_details.rate / 100
			else:
				tax_amount = net_total * tax_details.rate / 100

			# once tds is deducted, not need to add vouchers in the invoice
			voucher_wise_amount = {}
		else:
			tax_amount = get_tds_amount(ldc, parties, inv, tax_details, voucher_wise_amount)

	elif party_type == "Customer":
		if tax_deducted:
			# if already TCS is charged, then amount will be calculated based on 'Previous Row Total'
			if inv.doctype == "Sales Invoice":
				tax_amount = 0
			else:
				tax_amount = inv.base_tax_withholding_net_total * tax_details.rate / 100
		else:
			#  if no TCS has been charged in FY,
			# then chargeable value is "prev invoices + advances - advance_adjusted" value which cross the threshold
			tax_amount = get_tcs_amount(parties, inv, tax_details, vouchers, advance_vouchers)

	if cint(tax_details.round_off_tax_amount):
		tax_amount = normal_round(tax_amount)

	return tax_amount, tax_deducted, tax_deducted_on_advances, voucher_wise_amount


def is_tax_deducted_on_the_basis_of_inv(vouchers):
	return frappe.db.exists(
		"Purchase Taxes and Charges",
		{
			"parent": ["in", vouchers],
			"is_tax_withholding_account": 1,
			"parenttype": "Purchase Invoice",
			"base_tax_amount_after_discount_amount": [">", 0],
		},
	)


def get_invoice_vouchers(parties, tax_details, company, party_type="Supplier"):
	voucher_wise_amount = []
	vouchers = []

	ldcs = frappe.db.get_all(
		"Lower Deduction Certificate",
		filters={
			"valid_from": [">=", tax_details.from_date],
			"valid_upto": ["<=", tax_details.to_date],
			"company": company,
			"supplier": ["in", parties],
		},
		fields=["supplier", "valid_from", "valid_upto", "rate"],
	)

	doctype = "Purchase Invoice" if party_type == "Supplier" else "Sales Invoice"
	field = [
		"base_tax_withholding_net_total as base_net_total" if party_type == "Supplier" else "base_net_total",
		"name",
		"grand_total",
		"posting_date",
	]

	filters = {
		"company": company,
		frappe.scrub(party_type): ["in", parties],
		"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
		"is_opening": "No",
		"docstatus": 1,
	}

	if doctype != "Sales Invoice":
		filters.update(
			{"apply_tds": 1, "tax_withholding_category": tax_details.get("tax_withholding_category")}
		)

	invoices_details = frappe.get_all(doctype, filters=filters, fields=field)

	for d in invoices_details:
		d = frappe._dict(
			{
				"voucher_name": d.name,
				"voucher_type": doctype,
				"taxable_amount": d.base_net_total,
				"grand_total": d.grand_total,
				"posting_date": d.posting_date,
			}
		)

		if ldc := [x for x in ldcs if d.posting_date >= x.valid_from and d.posting_date <= x.valid_upto]:
			if ldc[0].supplier in parties and ldc[0].rate == 0:
				d.update({"taxable_amount": 0})

		vouchers.append(d.voucher_name)
		voucher_wise_amount.append(d)

	journal_entries_details = frappe.db.sql(
		"""
		SELECT j.name, ja.credit - ja.debit AS amount, ja.reference_type
			FROM `tabJournal Entry` j, `tabJournal Entry Account` ja
		WHERE
			j.name = ja.parent
			AND j.docstatus = 1
			AND j.is_opening = 'No'
			AND j.posting_date between %s and %s
			AND ja.party in %s
			AND j.apply_tds = 1
			AND j.tax_withholding_category = %s
			AND j.company = %s
	""",
		(
			tax_details.from_date,
			tax_details.to_date,
			tuple(parties),
			tax_details.get("tax_withholding_category"),
			company,
		),
		as_dict=1,
	)

	for d in journal_entries_details:
		vouchers.append(d.name)
		voucher_wise_amount.append(
			frappe._dict(
				{
					"voucher_name": d.name,
					"voucher_type": "Journal Entry",
					"taxable_amount": d.amount,
					"reference_type": d.reference_type,
				}
			)
		)

	return vouchers, voucher_wise_amount


def get_payment_entry_vouchers(parties, tax_details, company, party_type="Supplier"):
	payment_entry_filters = {
		"party_type": party_type,
		"party": ("in", parties),
		"docstatus": 1,
		"apply_tax_withholding_amount": 1,
		"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
		"tax_withholding_category": tax_details.get("tax_withholding_category"),
		"company": company,
	}

	return frappe.db.get_all("Payment Entry", filters=payment_entry_filters, pluck="name")


def get_advance_vouchers(parties, company=None, from_date=None, to_date=None, party_type="Supplier"):
	"""
	Use Payment Ledger to fetch unallocated Advance Payments
	"""

	if party_type == "Supplier":
		return []

	ple = qb.DocType("Payment Ledger Entry")

	conditions = []

	conditions.append(ple.amount.lt(0))
	conditions.append(ple.delinked == 0)
	conditions.append(ple.party_type == party_type)
	conditions.append(ple.party.isin(parties))
	conditions.append(ple.voucher_no == ple.against_voucher_no)

	if company:
		conditions.append(ple.company == company)

	if from_date and to_date:
		conditions.append(ple.posting_date[from_date:to_date])

	advances = qb.from_(ple).select(ple.voucher_no).distinct().where(Criterion.all(conditions)).run(as_list=1)
	if advances:
		advances = [x[0] for x in advances]

	return advances


def get_taxes_deducted_on_advances_allocated(inv, tax_details):
	tax_info = []

	if inv.get("advances"):
		advances = [d.reference_name for d in inv.get("advances")]

		if advances:
			pe = frappe.qb.DocType("Payment Entry").as_("pe")
			at = frappe.qb.DocType("Advance Taxes and Charges").as_("at")

			tax_info = (
				frappe.qb.from_(at)
				.inner_join(pe)
				.on(pe.name == at.parent)
				.select(pe.posting_date, at.parent, at.name, at.tax_amount, at.allocated_amount)
				.where(pe.tax_withholding_category == tax_details.get("tax_withholding_category"))
				.where(at.parent.isin(advances))
				.where(at.account_head == tax_details.account_head)
				.run(as_dict=True)
			)

	return tax_info


def get_deducted_tax(taxable_vouchers, tax_details):
	# check if TDS / TCS account is already charged on taxable vouchers
	filters = {
		"is_cancelled": 0,
		"credit": [">", 0],
		"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
		"account": tax_details.account_head,
		"voucher_no": ["in", taxable_vouchers],
	}
	field = "credit"

	entries = frappe.db.get_all("GL Entry", filters, pluck=field)
	return sum(entries)


def get_advance_tax_across_fiscal_year(tax_deducted_on_advances, tax_details):
	"""
	Only applies for Taxes deducted on Advance Payments
	"""
	advance_tax_from_across_fiscal_year = sum(
		[adv.tax_amount for adv in tax_deducted_on_advances if adv.posting_date < tax_details.from_date]
	)
	return advance_tax_from_across_fiscal_year


def get_tds_amount(ldc, parties, inv, tax_details, voucher_wise_amount):
	tds_amount = 0

	pi_grand_total = 0
	pi_base_net_total = 0
	jv_credit_amt = 0
	pe_credit_amt = 0

	for row in voucher_wise_amount:
		if row.voucher_type == "Purchase Invoice":
			pi_grand_total += row.get("grand_total", 0)
			pi_base_net_total += row.get("taxable_amount", 0)

		if row.voucher_type == "Journal Entry" and row.reference_type != "Purchase Invoice":
			jv_credit_amt += row.get("taxable_amount", 0)

	## for TDS to be deducted on advances
	pe_filters = {
		"party_type": "Supplier",
		"party": ("in", parties),
		"docstatus": 1,
		"apply_tax_withholding_amount": 1,
		"unallocated_amount": (">", 0),
		"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
		"tax_withholding_category": tax_details.get("tax_withholding_category"),
		"company": inv.company,
	}

	consider_party_ledger_amt = cint(tax_details.consider_party_ledger_amount)

	if consider_party_ledger_amt:
		pe_filters.pop("apply_tax_withholding_amount", None)
		pe_filters.pop("tax_withholding_category", None)

	# Get Amount via payment entry
	payment_entries = frappe.db.get_all(
		"Payment Entry",
		filters=pe_filters,
		fields=["name", "unallocated_amount as taxable_amount", "payment_type"],
	)

	for row in payment_entries:
		value = row.taxable_amount if row.payment_type == "Pay" else -1 * row.taxable_amount
		pe_credit_amt += value
		voucher_wise_amount.append(
			frappe._dict(
				{
					"voucher_name": row.name,
					"voucher_type": "Payment Entry",
					"taxable_amount": value,
				}
			)
		)

	threshold = tax_details.get("threshold", 0)
	cumulative_threshold = tax_details.get("cumulative_threshold", 0)
	supp_credit_amt = jv_credit_amt + pe_credit_amt + inv.get("tax_withholding_net_total", 0)
	tax_withholding_net_total = inv.get("base_tax_withholding_net_total", 0)

	# if consider_party_ledger_amount is checked, then threshold will be based on grand total
	amt_for_threshold = pi_grand_total if consider_party_ledger_amt else pi_base_net_total

	cumulative_threshold_breached = (
		cumulative_threshold and (supp_credit_amt + amt_for_threshold) >= cumulative_threshold
	)

	if (threshold and tax_withholding_net_total >= threshold) or (cumulative_threshold_breached):
		supp_credit_amt += pi_base_net_total

		if cumulative_threshold_breached and cint(tax_details.tax_on_excess_amount):
			supp_credit_amt = pi_base_net_total + tax_withholding_net_total - cumulative_threshold

		if ldc and is_valid_certificate(ldc, inv.get("posting_date") or inv.get("transaction_date"), 0):
			tds_amount = get_lower_deduction_amount(
				supp_credit_amt, 0, ldc.certificate_limit, ldc.rate, tax_details
			)
		else:
			tds_amount = supp_credit_amt * tax_details.rate / 100 if supp_credit_amt > 0 else 0

	return tds_amount


def get_tcs_amount(parties, inv, tax_details, vouchers, adv_vouchers):
	tcs_amount = 0
	ple = qb.DocType("Payment Ledger Entry")

	# sum of debit entries made from sales invoices
	invoiced_amt = (
		frappe.db.get_value(
			"GL Entry",
			{
				"is_cancelled": 0,
				"party_type": "Customer",
				"party": ["in", parties],
				"company": inv.company,
				"voucher_no": ["in", vouchers],
			},
			[{"SUM": "debit"}],
		)
		or 0.0
	)

	# sum of credit entries made from PE / JV with unset 'against voucher'

	conditions = []
	conditions.append(ple.amount.lt(0))
	conditions.append(ple.delinked == 0)
	conditions.append(ple.party_type == "Customer")
	conditions.append(ple.party.isin(parties))
	conditions.append(ple.voucher_no == ple.against_voucher_no)
	conditions.append(ple.company == inv.company)
	conditions.append(ple.posting_date[tax_details.from_date : tax_details.to_date])

	advance_amt = (
		qb.from_(ple).select(Abs(Sum(ple.amount))).where(Criterion.all(conditions)).run()[0][0] or 0.0
	)

	# sum of credit entries made from sales invoice
	credit_note_amt = sum(
		frappe.db.get_all(
			"GL Entry",
			{
				"is_cancelled": 0,
				"credit": [">", 0],
				"party_type": "Customer",
				"party": ["in", parties],
				"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
				"company": inv.company,
				"voucher_type": "Sales Invoice",
			},
			pluck="credit",
		)
	)

	cumulative_threshold = tax_details.get("cumulative_threshold", 0)
	advance_adjusted = get_advance_adjusted_in_invoice(inv)

	current_invoice_total = get_invoice_total_without_tcs(inv, tax_details)
	total_invoiced_amt = (
		current_invoice_total + invoiced_amt + advance_amt - credit_note_amt - advance_adjusted
	)

	if cumulative_threshold and total_invoiced_amt >= cumulative_threshold:
		chargeable_amt = total_invoiced_amt - cumulative_threshold
		tcs_amount = chargeable_amt * tax_details.rate / 100 if chargeable_amt > 0 else 0

	return tcs_amount


def get_advance_adjusted_in_invoice(inv):
	advances_adjusted = 0
	for row in inv.get("advances", []):
		advances_adjusted += row.allocated_amount

	return advances_adjusted


def get_invoice_total_without_tcs(inv, tax_details):
	tcs_tax_row = [d for d in inv.get("taxes") or [] if d.account_head == tax_details.account_head]
	tcs_tax_row_amount = tcs_tax_row[0].base_tax_amount if tcs_tax_row else 0

	return inv.grand_total - tcs_tax_row_amount


def get_limit_consumed(ldc, parties):
	limit_consumed = frappe.db.get_value(
		"Purchase Invoice",
		{
			"supplier": ("in", parties),
			"apply_tds": 1,
			"docstatus": 1,
			"tax_withholding_category": ldc.tax_withholding_category,
			"posting_date": ("between", (ldc.valid_from, ldc.valid_upto)),
			"company": ldc.company,
		},
		[{"SUM": "tax_withholding_net_total"}],
	)

	return limit_consumed


def get_lower_deduction_amount(current_amount, limit_consumed, certificate_limit, rate, tax_details):
	if certificate_limit - flt(limit_consumed) - flt(current_amount) >= 0:
		return current_amount * rate / 100
	else:
		ltds_amount = certificate_limit - flt(limit_consumed)
		tds_amount = current_amount - ltds_amount

		return ltds_amount * rate / 100 + tds_amount * tax_details.rate / 100


def is_valid_certificate(ldc, posting_date, limit_consumed):
	available_amount = flt(ldc.certificate_limit) - flt(limit_consumed)
	if (getdate(ldc.valid_from) <= getdate(posting_date) <= getdate(ldc.valid_upto)) and available_amount > 0:
		return True

	return False


def normal_round(number):
	"""
	Rounds a number to the nearest integer.
	:param number: The number to round.
	"""
	decimal_part = number - int(number)

	if decimal_part >= 0.5:
		decimal_part = 1
	else:
		decimal_part = 0

	number = int(number) + decimal_part

	return number
