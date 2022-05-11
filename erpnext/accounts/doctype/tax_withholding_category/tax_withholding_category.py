# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate


class TaxWithholdingCategory(Document):
	def validate(self):
		self.validate_dates()
		self.validate_accounts()
		self.validate_thresholds()

	def validate_dates(self):
		last_date = None
		for d in self.get("rates"):
			if getdate(d.from_date) >= getdate(d.to_date):
				frappe.throw(_("Row #{0}: From Date cannot be before To Date").format(d.idx))

			# validate overlapping of dates
			if last_date and getdate(d.to_date) < getdate(last_date):
				frappe.throw(_("Row #{0}: Dates overlapping with other row").format(d.idx))

	def validate_accounts(self):
		existing_accounts = []
		for d in self.get("accounts"):
			if d.get("account") in existing_accounts:
				frappe.throw(_("Account {0} added multiple times").format(frappe.bold(d.get("account"))))

			existing_accounts.append(d.get("account"))

	def validate_thresholds(self):
		for d in self.get("rates"):
			if (
				d.cumulative_threshold and d.single_threshold and d.cumulative_threshold < d.single_threshold
			):
				frappe.throw(
					_("Row #{0}: Cumulative threshold cannot be less than Single Transaction threshold").format(
						d.idx
					)
				)


def get_party_details(inv):
	party_type, party = "", ""

	if inv.doctype == "Sales Invoice":
		party_type = "Customer"
		party = inv.customer
	else:
		party_type = "Supplier"
		party = inv.supplier

	if not party:
		frappe.throw(_("Please select {0} first").format(party_type))

	return party_type, party


def get_party_tax_withholding_details(inv, tax_withholding_category=None):
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
		frappe.throw(
			_("Please set associated account in Tax Withholding Category {0} against Company {1}").format(
				tax_withholding_category, inv.company
			)
		)

	if party_type == "Customer" and not tax_details.cumulative_threshold:
		# TCS is only chargeable on sum of invoiced value
		frappe.throw(
			_(
				"Tax Withholding Category {} against Company {} for Customer {} should have Cumulative Threshold value."
			).format(tax_withholding_category, inv.company, party)
		)

	tax_amount, tax_deducted, tax_deducted_on_advances = get_tax_amount(
		party_type, parties, inv, tax_details, posting_date, pan_no
	)

	if party_type == "Supplier":
		tax_row = get_tax_row_for_tds(tax_details, tax_amount)
	else:
		tax_row = get_tax_row_for_tcs(inv, tax_details, tax_amount, tax_deducted)

	if inv.doctype == "Purchase Invoice":
		return tax_row, tax_deducted_on_advances
	else:
		return tax_row


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


def get_lower_deduction_certificate(tax_details, pan_no):
	ldc_name = frappe.db.get_value(
		"Lower Deduction Certificate",
		{
			"pan_no": pan_no,
			"tax_withholding_category": tax_details.tax_withholding_category,
			"valid_from": (">=", tax_details.from_date),
			"valid_upto": ("<=", tax_details.to_date),
		},
		"name",
	)

	if ldc_name:
		return frappe.get_doc("Lower Deduction Certificate", ldc_name)


def get_tax_amount(party_type, parties, inv, tax_details, posting_date, pan_no=None):
	vouchers = get_invoice_vouchers(parties, tax_details, inv.company, party_type=party_type)
	advance_vouchers = get_advance_vouchers(
		parties,
		company=inv.company,
		from_date=tax_details.from_date,
		to_date=tax_details.to_date,
		party_type=party_type,
	)
	taxable_vouchers = vouchers + advance_vouchers
	tax_deducted_on_advances = 0

	if inv.doctype == "Purchase Invoice":
		tax_deducted_on_advances = get_taxes_deducted_on_advances_allocated(inv, tax_details)

	tax_deducted = 0
	if taxable_vouchers:
		tax_deducted = get_deducted_tax(taxable_vouchers, tax_details)

	tax_amount = 0
	if party_type == "Supplier":
		ldc = get_lower_deduction_certificate(tax_details, pan_no)
		if tax_deducted:
			net_total = inv.net_total
			if ldc:
				tax_amount = get_tds_amount_from_ldc(
					ldc, parties, pan_no, tax_details, posting_date, net_total
				)
			else:
				tax_amount = net_total * tax_details.rate / 100 if net_total > 0 else 0
		else:
			tax_amount = get_tds_amount(ldc, parties, inv, tax_details, tax_deducted, vouchers)

	elif party_type == "Customer":
		if tax_deducted:
			# if already TCS is charged, then amount will be calculated based on 'Previous Row Total'
			tax_amount = 0
		else:
			#  if no TCS has been charged in FY,
			# then chargeable value is "prev invoices + advances" value which cross the threshold
			tax_amount = get_tcs_amount(parties, inv, tax_details, vouchers, advance_vouchers)

	if cint(tax_details.round_off_tax_amount):
		tax_amount = round(tax_amount)

	return tax_amount, tax_deducted, tax_deducted_on_advances


def get_invoice_vouchers(parties, tax_details, company, party_type="Supplier"):
	dr_or_cr = "credit" if party_type == "Supplier" else "debit"
	doctype = "Purchase Invoice" if party_type == "Supplier" else "Sales Invoice"

	filters = {
		"company": company,
		frappe.scrub(party_type): ["in", parties],
		"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
		"is_opening": "No",
		"docstatus": 1,
	}

	if not tax_details.get("consider_party_ledger_amount") and doctype != "Sales Invoice":
		filters.update(
			{"apply_tds": 1, "tax_withholding_category": tax_details.get("tax_withholding_category")}
		)

	invoices = frappe.get_all(doctype, filters=filters, pluck="name") or [""]

	journal_entries = frappe.db.sql(
		"""
		SELECT j.name
			FROM `tabJournal Entry` j, `tabJournal Entry Account` ja
		WHERE
			j.docstatus = 1
			AND j.is_opening = 'No'
			AND j.posting_date between %s and %s
			AND ja.{dr_or_cr} > 0
			AND ja.party in %s
	""".format(
			dr_or_cr=dr_or_cr
		),
		(tax_details.from_date, tax_details.to_date, tuple(parties)),
		as_list=1,
	)

	if journal_entries:
		journal_entries = journal_entries[0]

	return invoices + journal_entries


def get_advance_vouchers(
	parties, company=None, from_date=None, to_date=None, party_type="Supplier"
):
	# for advance vouchers, debit and credit is reversed
	dr_or_cr = "debit" if party_type == "Supplier" else "credit"

	filters = {
		dr_or_cr: [">", 0],
		"is_opening": "No",
		"is_cancelled": 0,
		"party_type": party_type,
		"party": ["in", parties],
		"against_voucher": ["is", "not set"],
	}

	if company:
		filters["company"] = company
	if from_date and to_date:
		filters["posting_date"] = ["between", (from_date, to_date)]

	return frappe.get_all("GL Entry", filters=filters, distinct=1, pluck="voucher_no") or [""]


def get_taxes_deducted_on_advances_allocated(inv, tax_details):
	advances = [d.reference_name for d in inv.get("advances")]
	tax_info = []

	if advances:
		pe = frappe.qb.DocType("Payment Entry").as_("pe")
		at = frappe.qb.DocType("Advance Taxes and Charges").as_("at")

		tax_info = (
			frappe.qb.from_(at)
			.inner_join(pe)
			.on(pe.name == at.parent)
			.select(at.parent, at.name, at.tax_amount, at.allocated_amount)
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


def get_tds_amount(ldc, parties, inv, tax_details, tax_deducted, vouchers):
	tds_amount = 0
	invoice_filters = {"name": ("in", vouchers), "docstatus": 1, "apply_tds": 1}

	field = "sum(net_total)"

	if cint(tax_details.consider_party_ledger_amount):
		invoice_filters.pop("apply_tds", None)
		field = "sum(grand_total)"

	supp_credit_amt = frappe.db.get_value("Purchase Invoice", invoice_filters, field) or 0.0

	supp_jv_credit_amt = (
		frappe.db.get_value(
			"Journal Entry Account",
			{
				"parent": ("in", vouchers),
				"docstatus": 1,
				"party": ("in", parties),
				"reference_type": ("!=", "Purchase Invoice"),
			},
			"sum(credit_in_account_currency)",
		)
		or 0.0
	)

	supp_credit_amt += supp_jv_credit_amt
	supp_credit_amt += inv.net_total

	debit_note_amount = get_debit_note_amount(
		parties, tax_details.from_date, tax_details.to_date, inv.company
	)
	supp_credit_amt -= debit_note_amount

	threshold = tax_details.get("threshold", 0)
	cumulative_threshold = tax_details.get("cumulative_threshold", 0)

	if (threshold and inv.net_total >= threshold) or (
		cumulative_threshold and supp_credit_amt >= cumulative_threshold
	):
		if (cumulative_threshold and supp_credit_amt >= cumulative_threshold) and cint(
			tax_details.tax_on_excess_amount
		):
			# Get net total again as TDS is calculated on net total
			# Grand is used to just check for threshold breach
			net_total = frappe.db.get_value("Purchase Invoice", invoice_filters, "sum(net_total)") or 0.0
			net_total += inv.net_total
			supp_credit_amt = net_total - cumulative_threshold

		if ldc and is_valid_certificate(
			ldc.valid_from,
			ldc.valid_upto,
			inv.get("posting_date") or inv.get("transaction_date"),
			tax_deducted,
			inv.net_total,
			ldc.certificate_limit,
		):
			tds_amount = get_ltds_amount(supp_credit_amt, 0, ldc.certificate_limit, ldc.rate, tax_details)
		else:
			tds_amount = supp_credit_amt * tax_details.rate / 100 if supp_credit_amt > 0 else 0

	return tds_amount


def get_tcs_amount(parties, inv, tax_details, vouchers, adv_vouchers):
	tcs_amount = 0

	# sum of debit entries made from sales invoices
	invoiced_amt = (
		frappe.db.get_value(
			"GL Entry",
			{
				"is_cancelled": 0,
				"party": ["in", parties],
				"company": inv.company,
				"voucher_no": ["in", vouchers],
			},
			"sum(debit)",
		)
		or 0.0
	)

	# sum of credit entries made from PE / JV with unset 'against voucher'
	advance_amt = (
		frappe.db.get_value(
			"GL Entry",
			{
				"is_cancelled": 0,
				"party": ["in", parties],
				"company": inv.company,
				"voucher_no": ["in", adv_vouchers],
			},
			"sum(credit)",
		)
		or 0.0
	)

	# sum of credit entries made from sales invoice
	credit_note_amt = sum(
		frappe.db.get_all(
			"GL Entry",
			{
				"is_cancelled": 0,
				"credit": [">", 0],
				"party": ["in", parties],
				"posting_date": ["between", (tax_details.from_date, tax_details.to_date)],
				"company": inv.company,
				"voucher_type": "Sales Invoice",
			},
			pluck="credit",
		)
	)

	cumulative_threshold = tax_details.get("cumulative_threshold", 0)

	current_invoice_total = get_invoice_total_without_tcs(inv, tax_details)
	total_invoiced_amt = current_invoice_total + invoiced_amt + advance_amt - credit_note_amt

	if cumulative_threshold and total_invoiced_amt >= cumulative_threshold:
		chargeable_amt = total_invoiced_amt - cumulative_threshold
		tcs_amount = chargeable_amt * tax_details.rate / 100 if chargeable_amt > 0 else 0

	return tcs_amount


def get_invoice_total_without_tcs(inv, tax_details):
	tcs_tax_row = [d for d in inv.taxes if d.account_head == tax_details.account_head]
	tcs_tax_row_amount = tcs_tax_row[0].base_tax_amount if tcs_tax_row else 0

	return inv.grand_total - tcs_tax_row_amount


def get_tds_amount_from_ldc(ldc, parties, pan_no, tax_details, posting_date, net_total):
	tds_amount = 0
	limit_consumed = frappe.db.get_value(
		"Purchase Invoice",
		{"supplier": ("in", parties), "apply_tds": 1, "docstatus": 1},
		"sum(net_total)",
	)

	if is_valid_certificate(
		ldc.valid_from, ldc.valid_upto, posting_date, limit_consumed, net_total, ldc.certificate_limit
	):
		tds_amount = get_ltds_amount(
			net_total, limit_consumed, ldc.certificate_limit, ldc.rate, tax_details
		)

	return tds_amount


def get_debit_note_amount(suppliers, from_date, to_date, company=None):

	filters = {
		"supplier": ["in", suppliers],
		"is_return": 1,
		"docstatus": 1,
		"posting_date": ["between", (from_date, to_date)],
	}
	fields = ["abs(sum(net_total)) as net_total"]

	if company:
		filters["company"] = company

	return frappe.get_all("Purchase Invoice", filters, fields)[0].get("net_total") or 0.0


def get_ltds_amount(current_amount, deducted_amount, certificate_limit, rate, tax_details):
	if current_amount < (certificate_limit - deducted_amount):
		return current_amount * rate / 100
	else:
		ltds_amount = certificate_limit - deducted_amount
		tds_amount = current_amount - ltds_amount

		return ltds_amount * rate / 100 + tds_amount * tax_details.rate / 100


def is_valid_certificate(
	valid_from, valid_upto, posting_date, deducted_amount, current_amount, certificate_limit
):
	valid = False

	if (
		getdate(valid_from) <= getdate(posting_date) <= getdate(valid_upto)
	) and certificate_limit > deducted_amount:
		valid = True

	return valid
