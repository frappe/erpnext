import frappe
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Sum
from frappe.utils import flt, formatdate, get_datetime_str, get_table_name
from pypika import Order

from erpnext import get_company_currency, get_default_company
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from erpnext.accounts.doctype.fiscal_year.fiscal_year import get_from_and_to_date
from erpnext.accounts.party import get_party_account
from erpnext.setup.utils import get_exchange_rate

__exchange_rates = {}


def get_currency(filters):
	"""
	Returns a dictionary containing currency information. The keys of the dict are
	- company: The company for which we are fetching currency information. if no
	company is specified, it will fallback to the default company.
	- company currency: The functional currency of the said company.
	- presentation currency: The presentation currency to use. Only currencies that
	have been used for transactions will be allowed.
	- report date: The report date.
	:param filters: Report filters
	:type filters: dict

	:return: str - Currency
	"""
	company = get_appropriate_company(filters)
	company_currency = get_company_currency(company)
	presentation_currency = (
		filters["presentation_currency"] if filters.get("presentation_currency") else company_currency
	)

	report_date = filters.get("to_date") or filters.get("period_end_date")

	if not report_date:
		fiscal_year_to_date = get_from_and_to_date(filters.get("to_fiscal_year"))["to_date"]
		report_date = formatdate(get_datetime_str(fiscal_year_to_date), "dd-MM-yyyy")

	currency_map = dict(
		company=company,
		company_currency=company_currency,
		presentation_currency=presentation_currency,
		report_date=report_date,
	)

	return currency_map


def convert(value, from_, to, date):
	"""
	convert `value` from `from_` to `to` on `date`
	:param value: Amount to be converted
	:param from_: Currency of `value`
	:param to: Currency to convert to
	:param date: exchange rate as at this date
	:return: Result of converting `value`
	"""
	rate = get_rate_as_at(date, from_, to)
	converted_value = flt(value) / (rate or 1)
	return converted_value


def get_rate_as_at(date, from_currency, to_currency):
	"""
	Gets exchange rate as at `date` for `from_currency` - `to_currency` exchange rate.
	This calls `get_exchange_rate` so that we can get the correct exchange rate as per
	the user's Accounts Settings.
	It is made efficient by memoising results to `__exchange_rates`
	:param date: exchange rate as at this date
	:param from_currency: Base currency
	:param to_currency: Quote currency
	:return: Retrieved exchange rate
	"""

	rate = __exchange_rates.get(f"{from_currency}-{to_currency}@{date}")
	if not rate:
		rate = get_exchange_rate(from_currency, to_currency, date) or 1
		__exchange_rates[f"{from_currency}-{to_currency}@{date}"] = rate

	return rate


def convert_to_presentation_currency(gl_entries, currency_info):
	"""
	Take a list of GL Entries and change the 'debit' and 'credit' values to currencies
	in `currency_info`.
	:param gl_entries:
	:param currency_info:
	:return:
	"""
	converted_gl_list = []
	presentation_currency = currency_info["presentation_currency"]
	company_currency = currency_info["company_currency"]

	account_currencies = list(set(entry["account_currency"] for entry in gl_entries))

	for entry in gl_entries:
		debit = flt(entry["debit"])
		credit = flt(entry["credit"])
		debit_in_account_currency = flt(entry["debit_in_account_currency"])
		credit_in_account_currency = flt(entry["credit_in_account_currency"])
		account_currency = entry["account_currency"]

		if len(account_currencies) == 1 and account_currency == presentation_currency:
			entry["debit"] = debit_in_account_currency
			entry["credit"] = credit_in_account_currency
		else:
			date = currency_info["report_date"]
			converted_debit_value = convert(debit, presentation_currency, company_currency, date)
			converted_credit_value = convert(credit, presentation_currency, company_currency, date)

			if entry.get("debit"):
				entry["debit"] = converted_debit_value

			if entry.get("credit"):
				entry["credit"] = converted_credit_value

		converted_gl_list.append(entry)

	return converted_gl_list


def get_appropriate_company(filters):
	if filters.get("company"):
		company = filters["company"]
	else:
		company = get_default_company()

	return company


@frappe.whitelist()
def get_invoiced_item_gross_margin(sales_invoice=None, item_code=None, company=None, with_item_data=False):
	from erpnext.accounts.report.gross_profit.gross_profit import GrossProfitGenerator

	sales_invoice = sales_invoice or frappe.form_dict.get("sales_invoice")
	item_code = item_code or frappe.form_dict.get("item_code")
	company = company or frappe.get_cached_value("Sales Invoice", sales_invoice, "company")

	filters = {
		"sales_invoice": sales_invoice,
		"item_code": item_code,
		"company": company,
		"group_by": "Invoice",
	}

	gross_profit_data = GrossProfitGenerator(filters)
	result = gross_profit_data.grouped_data
	if not with_item_data:
		result = sum(d.gross_profit for d in result)

	return result


def get_query_columns(report_columns):
	if not report_columns:
		return ""

	columns = []
	for column in report_columns:
		fieldname = column["fieldname"]

		if doctype := column.get("_doctype"):
			columns.append(f"`{get_table_name(doctype)}`.`{fieldname}`")
		else:
			columns.append(fieldname)

	return columns


def get_values_for_columns(report_columns, report_row):
	values = {}

	if not report_columns:
		return values

	for column in report_columns:
		fieldname = column["fieldname"]
		values[fieldname] = report_row.get(fieldname)

	return values


def get_party_details(party_type, party_list):
	party_details = {}
	party = frappe.qb.DocType(party_type)
	query = frappe.qb.from_(party).select(party.name, party.tax_id).where(party.name.isin(party_list))
	if party_type == "Supplier":
		query = query.select(party.supplier_group)
	else:
		query = query.select(party.customer_group, party.territory)

	party_detail_list = query.run(as_dict=True)
	for party_dict in party_detail_list:
		party_details[party_dict.name] = party_dict
	return party_details


def get_taxes_query(invoice_list, doctype, parenttype):
	taxes = frappe.qb.DocType(doctype)

	query = (
		frappe.qb.from_(taxes)
		.select(taxes.account_head)
		.distinct()
		.where(
			(taxes.parenttype == parenttype)
			& (taxes.docstatus == 1)
			& (taxes.account_head.isnotnull())
			& (taxes.parent.isin([inv.name for inv in invoice_list]))
		)
		.orderby(taxes.account_head)
	)

	if doctype == "Purchase Taxes and Charges":
		return query.where(taxes.category.isin(["Total", "Valuation and Total"]))
	elif doctype == "Sales Taxes and Charges":
		return query
	return query.where(taxes.charge_type.isin(["On Paid Amount", "Actual"]))


def get_journal_entries(filters, args):
	je = frappe.qb.DocType("Journal Entry")
	journal_account = frappe.qb.DocType("Journal Entry Account")
	query = (
		frappe.qb.from_(je)
		.inner_join(journal_account)
		.on(je.name == journal_account.parent)
		.select(
			je.voucher_type.as_("doctype"),
			je.name,
			je.posting_date,
			journal_account.account.as_(args.account),
			journal_account.party.as_(args.party),
			journal_account.party.as_(args.party_name),
			je.bill_no,
			je.bill_date,
			je.remark.as_("remarks"),
			je.total_amount.as_("base_net_total"),
			je.total_amount.as_("base_grand_total"),
			je.mode_of_payment,
			journal_account.project,
		)
		.where(
			(je.voucher_type == "Journal Entry")
			& (je.docstatus == 1)
			& (journal_account.party == filters.get(args.party))
			& (journal_account.account.isin(args.party_account))
		)
		.orderby(je.posting_date, je.name, order=Order.desc)
	)
	query = apply_common_conditions(filters, query, doctype="Journal Entry", payments=True)

	journal_entries = query.run(as_dict=True)
	return journal_entries


def get_payment_entries(filters, args):
	pe = frappe.qb.DocType("Payment Entry")
	query = (
		frappe.qb.from_(pe)
		.select(
			ConstantColumn("Payment Entry").as_("doctype"),
			pe.name,
			pe.posting_date,
			pe[args.account_fieldname].as_(args.account),
			pe.party.as_(args.party),
			pe.party_name.as_(args.party_name),
			pe.remarks,
			pe.paid_amount.as_("base_net_total"),
			pe.paid_amount_after_tax.as_("base_grand_total"),
			pe.mode_of_payment,
			pe.project,
			pe.cost_center,
		)
		.where(
			(pe.docstatus == 1)
			& (pe.party == filters.get(args.party))
			& (pe[args.account_fieldname].isin(args.party_account))
		)
		.orderby(pe.posting_date, pe.name, order=Order.desc)
	)
	query = apply_common_conditions(filters, query, doctype="Payment Entry", payments=True)
	payment_entries = query.run(as_dict=True)
	return payment_entries


def apply_common_conditions(filters, query, doctype, child_doctype=None, payments=False):
	parent_doc = frappe.qb.DocType(doctype)
	if child_doctype:
		child_doc = frappe.qb.DocType(child_doctype)

	join_required = False

	if filters.get("company"):
		query = query.where(parent_doc.company == filters.company)
	if filters.get("from_date"):
		query = query.where(parent_doc.posting_date >= filters.from_date)
	if filters.get("to_date"):
		query = query.where(parent_doc.posting_date <= filters.to_date)

	if payments:
		if filters.get("cost_center"):
			query = query.where(parent_doc.cost_center == filters.cost_center)
	else:
		if filters.get("cost_center"):
			query = query.where(child_doc.cost_center == filters.cost_center)
			join_required = True
		if filters.get("warehouse"):
			query = query.where(child_doc.warehouse == filters.warehouse)
			join_required = True
		if filters.get("item_group"):
			query = query.where(child_doc.item_group == filters.item_group)
			join_required = True

	if not payments:
		if filters.get("brand"):
			query = query.where(child_doc.brand == filters.brand)
			join_required = True

	if join_required:
		query = query.inner_join(child_doc).on(parent_doc.name == child_doc.parent)
		query = query.distinct()

	if parent_doc.get_table_name() != "tabJournal Entry":
		query = filter_invoices_based_on_dimensions(filters, query, parent_doc)

	return query


def get_advance_taxes_and_charges(invoice_list):
	adv_taxes = frappe.qb.DocType("Advance Taxes and Charges")
	return (
		frappe.qb.from_(adv_taxes)
		.select(
			adv_taxes.parent,
			adv_taxes.account_head,
			(
				frappe.qb.terms.Case()
				.when(adv_taxes.add_deduct_tax == "Add", Sum(adv_taxes.base_tax_amount))
				.else_(Sum(adv_taxes.base_tax_amount) * -1)
			).as_("tax_amount"),
		)
		.where(
			(adv_taxes.parent.isin([inv.name for inv in invoice_list]))
			& (adv_taxes.charge_type.isin(["On Paid Amount", "Actual"]))
			& (adv_taxes.base_tax_amount != 0)
		)
		.groupby(adv_taxes.parent, adv_taxes.account_head, adv_taxes.add_deduct_tax)
	).run(as_dict=True)


def filter_invoices_based_on_dimensions(filters, query, parent_doc):
	accounting_dimensions = get_accounting_dimensions(as_list=False)
	if accounting_dimensions:
		for dimension in accounting_dimensions:
			if filters.get(dimension.fieldname):
				if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
					filters[dimension.fieldname] = get_dimension_with_children(
						dimension.document_type, filters.get(dimension.fieldname)
					)
				fieldname = dimension.fieldname
				query = query.where(parent_doc[fieldname].isin(filters[fieldname]))
	return query


def get_opening_row(party_type, party, from_date, company):
	party_account = get_party_account(party_type, party, company, include_advance=True)
	gle = frappe.qb.DocType("GL Entry")
	return (
		frappe.qb.from_(gle)
		.select(
			ConstantColumn("Opening").as_("account"),
			Sum(gle.debit).as_("debit"),
			Sum(gle.credit).as_("credit"),
			(Sum(gle.debit) - Sum(gle.credit)).as_("balance"),
		)
		.where(
			(gle.account.isin(party_account))
			& (gle.party == party)
			& (gle.posting_date < from_date)
			& (gle.is_cancelled == 0)
		)
	).run(as_dict=True)
