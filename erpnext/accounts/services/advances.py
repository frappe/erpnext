# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Advance payment query and management functions.

All functions take a `doc` (AccountsController instance) as first argument so
they can be called as module-level functions from any doctype, while keeping
the AccountsController methods as thin shims.
"""

import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Abs, Sum
from frappe.utils import flt

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_dimensions,
)
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_account_currency, get_advance_payment_doctypes
from erpnext.setup.utils import get_exchange_rate


def set_advances(doc) -> None:
	"""Populate the advances child table from open advance entries."""
	res = get_advance_entries(
		doc, include_unallocated=not frappe.utils.cint(doc.get("only_include_allocated_payments"))
	)

	doc.set("advances", [])
	advance_allocated = 0
	for d in res:
		if doc.get("party_account_currency") == doc.company_currency:
			amount = doc.get("base_rounded_total") or doc.base_grand_total
		else:
			amount = doc.get("rounded_total") or doc.grand_total
		allocated_amount = min(amount - advance_allocated, d.amount)
		advance_allocated += flt(allocated_amount)

		advance_row = {
			"doctype": doc.doctype + " Advance",
			"reference_type": d.reference_type,
			"reference_name": d.reference_name,
			"reference_row": d.reference_row,
			"remarks": d.remarks,
			"advance_amount": flt(d.amount),
			"allocated_amount": allocated_amount,
			"ref_exchange_rate": flt(d.exchange_rate),
			"difference_posting_date": doc.posting_date,
		}
		if d.get("paid_from"):
			advance_row["account"] = d.paid_from
		if d.get("paid_to"):
			advance_row["account"] = d.paid_to

		doc.append("advances", advance_row)


def get_advance_entries(doc, include_unallocated: bool = True) -> list:
	"""Return advance journal and payment entries applicable to `doc`."""
	party_account = []
	default_advance_account = None

	if doc.doctype in ["Sales Invoice", "POS Invoice"]:
		party_type = "Customer"
		party = doc.customer
		amount_field = "credit_in_account_currency"
		order_field = "sales_order"
		order_doctype = "Sales Order"
		party_account.append(doc.debit_to)
	else:
		party_type = "Supplier"
		party = doc.supplier
		amount_field = "debit_in_account_currency"
		order_field = "purchase_order"
		order_doctype = "Purchase Order"
		party_account.append(doc.credit_to)

	party_accounts = get_party_account(party_type, party=party, company=doc.company, include_advance=True)

	if party_accounts:
		party_account.append(party_accounts[0])
		default_advance_account = party_accounts[1] if len(party_accounts) == 2 else None

	order_list = list(set(d.get(order_field) for d in doc.get("items") if d.get(order_field)))

	journal_entries = get_advance_journal_entries(
		party_type, party, party_account, amount_field, order_doctype, order_list, include_unallocated
	)

	payment_entries = get_advance_payment_entries_for_regional(
		party_type,
		party,
		party_account,
		order_doctype,
		order_list,
		default_advance_account,
		include_unallocated,
	)

	return journal_entries + payment_entries


def validate_advance_entries(doc) -> None:
	"""Warn if a payment entry linked to the same order is not pulled as advance."""
	order_field = "sales_order" if doc.doctype == "Sales Invoice" else "purchase_order"
	order_list = list(set(d.get(order_field) for d in doc.get("items") if d.get(order_field)))

	if not order_list:
		return

	advance_entries = get_advance_entries(doc, include_unallocated=False)

	if advance_entries:
		advance_entries_against_si = [d.reference_name for d in doc.get("advances")]
		for d in advance_entries:
			if not advance_entries_against_si or d.reference_name not in advance_entries_against_si:
				frappe.msgprint(
					_(
						"Payment Entry {0} is linked against Order {1}, check if it should be pulled as advance in this invoice."
					).format(d.reference_name, d.against_order)
				)


def set_advance_gain_or_loss(doc) -> None:
	"""Compute exchange gain/loss for each allocated advance row."""
	if doc.get("conversion_rate") == 1 or not doc.get("advances"):
		return

	is_purchase_invoice = doc.doctype == "Purchase Invoice"
	party_account = doc.credit_to if is_purchase_invoice else doc.debit_to
	if get_account_currency(party_account) != doc.currency:
		return

	for d in doc.get("advances"):
		advance_exchange_rate = d.ref_exchange_rate
		if d.allocated_amount and doc.conversion_rate != advance_exchange_rate:
			base_allocated_amount_in_ref_rate = advance_exchange_rate * d.allocated_amount
			base_allocated_amount_in_inv_rate = doc.conversion_rate * d.allocated_amount
			difference = base_allocated_amount_in_ref_rate - base_allocated_amount_in_inv_rate

			d.exchange_gain_loss = difference


def calculate_total_advance_from_ledger(doc) -> list:
	"""Query the Advance Payment Ledger for the total advance against `doc`."""
	adv = frappe.qb.DocType("Advance Payment Ledger Entry")
	return (
		frappe.qb.from_(adv)
		.select(Abs(Sum(adv.amount)).as_("amount"), adv.currency.as_("account_currency"))
		.where(adv.company == doc.company)
		.where(adv.delinked == 0)
		.where(adv.against_voucher_type == doc.doctype)
		.where(adv.against_voucher_no == doc.name)
		.run(as_dict=True)
	)


def set_total_advance_paid(doc) -> None:
	"""Update advance_paid field and payment status from the ledger."""
	advance = calculate_total_advance_from_ledger(doc)
	advance_paid = 0

	if advance:
		advance = advance[0]
		advance_paid = flt(advance.amount, doc.precision("advance_paid"))
		if advance.account_currency:
			frappe.db.set_value(doc.doctype, doc.name, "party_account_currency", advance.account_currency)

	doc.db_set("advance_paid", advance_paid)
	set_advance_payment_status(doc)


def set_advance_payment_status(doc) -> None:
	"""Sync advance_payment_status with current ledger and Payment Request state."""
	new_status = None

	PaymentRequest = frappe.qb.DocType("Payment Request")
	paid_amount = frappe.get_value(
		doctype="Payment Request",
		filters={
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"docstatus": 1,
		},
		fieldname=Sum(PaymentRequest.grand_total - PaymentRequest.outstanding_amount),
	)

	if not paid_amount:
		if doc.doctype in get_advance_payment_doctypes(payment_type="receivable"):
			new_status = "Not Requested" if paid_amount is None else "Requested"
		elif doc.doctype in get_advance_payment_doctypes(payment_type="payable"):
			new_status = "Not Initiated" if paid_amount is None else "Initiated"
	else:
		total_amount = doc.get("rounded_total") or doc.get("grand_total")
		new_status = "Fully Paid" if paid_amount == total_amount else "Partially Paid"

	if new_status == doc.advance_payment_status:
		return

	doc.db_set("advance_payment_status", new_status, update_modified=False)
	doc.set_status(update=True)
	doc.notify_update()


def delink_advance_entries(doc, linked_doc_name: str) -> None:
	"""Remove advance rows linked to `linked_doc_name` and update total_advance."""
	total_allocated_amount = 0
	for adv in doc.advances:
		consider_for_total_advance = True
		if adv.reference_name == linked_doc_name:
			doctype = frappe.qb.DocType(doc.doctype + " Advance")
			frappe.qb.from_(doctype).delete().where(doctype.name == adv.name).run()

			consider_for_total_advance = False

		if consider_for_total_advance:
			total_allocated_amount += flt(adv.allocated_amount, adv.precision("allocated_amount"))

	frappe.db.set_value(doc.doctype, doc.name, "total_advance", total_allocated_amount, update_modified=False)


def create_advance_and_reconcile(doc, party_link) -> None:
	"""Create a Journal Entry to reconcile a party-link advance."""
	secondary_party_type, secondary_party = doc.get_party()
	primary_party_type, primary_party = party_link.primary_role, party_link.primary_party

	primary_account = get_party_account(primary_party_type, primary_party, doc.company)
	secondary_account = get_party_account(secondary_party_type, secondary_party, doc.company)
	primary_account_currency = get_account_currency(primary_account)
	secondary_account_currency = get_account_currency(secondary_account)
	default_currency = erpnext.get_company_currency(doc.company)

	multi_currency = (
		primary_account_currency != default_currency or secondary_account_currency != default_currency
	)

	jv = frappe.new_doc("Journal Entry")
	jv.voucher_type = "Journal Entry"
	jv.posting_date = doc.posting_date
	jv.company = doc.company
	jv.remark = f"Adjustment for {doc.doctype} {doc.name}"
	jv.is_system_generated = True

	reconcilation_entry = frappe._dict()
	advance_entry = frappe._dict()

	reconcilation_entry.account = secondary_account
	reconcilation_entry.party_type = secondary_party_type
	reconcilation_entry.party = secondary_party
	reconcilation_entry.reference_type = doc.doctype
	reconcilation_entry.reference_name = doc.name
	reconcilation_entry.cost_center = doc.cost_center or erpnext.get_default_cost_center(doc.company)

	advance_entry.account = primary_account
	advance_entry.party_type = primary_party_type
	advance_entry.party = primary_party
	advance_entry.cost_center = doc.cost_center or erpnext.get_default_cost_center(doc.company)
	advance_entry.is_advance = "No" if doc.is_return else "Yes"

	dimensions_dict = frappe._dict()
	active_dimensions = get_dimensions()[0]
	for dim in active_dimensions:
		dimensions_dict[dim.fieldname] = doc.get(dim.fieldname)

	reconcilation_entry.update(dimensions_dict)
	advance_entry.update(dimensions_dict)

	if multi_currency:
		exc_rate_primary_to_default = (
			1
			if primary_account_currency == default_currency
			else get_exchange_rate(primary_account_currency, default_currency, doc.posting_date)
		)
		exc_rate_secondary_to_default = (
			1
			if secondary_account_currency == default_currency
			else get_exchange_rate(secondary_account_currency, default_currency, doc.posting_date)
		)
		exc_rate_secondary_to_primary = (
			1
			if secondary_account_currency == primary_account_currency
			else get_exchange_rate(secondary_account_currency, primary_account_currency, doc.posting_date)
		)

		outstanding_amount = abs(doc.outstanding_amount)
		os_in_default_currency = outstanding_amount * exc_rate_secondary_to_default
		os_in_primary_currency = outstanding_amount * exc_rate_secondary_to_primary

		reconciliation_is_credit = (doc.doctype == "Sales Invoice") != bool(doc.is_return)
		_set_je_amounts(
			reconcilation_entry, outstanding_amount, os_in_default_currency, reconciliation_is_credit
		)
		_set_je_amounts(
			advance_entry, os_in_primary_currency, os_in_default_currency, not reconciliation_is_credit
		)

		reconcilation_entry.exchange_rate = exc_rate_secondary_to_default
		advance_entry.exchange_rate = exc_rate_primary_to_default
	else:
		outstanding_amount = abs(doc.outstanding_amount)
		reconciliation_is_credit = (doc.doctype == "Sales Invoice") != bool(doc.is_return)
		_set_je_amounts(reconcilation_entry, outstanding_amount, is_credit=reconciliation_is_credit)
		_set_je_amounts(advance_entry, outstanding_amount, is_credit=not reconciliation_is_credit)

	jv.multi_currency = multi_currency
	jv.append("accounts", reconcilation_entry)
	jv.append("accounts", advance_entry)

	jv.save()
	jv.submit()


def get_advance_journal_entries(
	party_type: str,
	party: str,
	party_account: list,
	amount_field: str,
	order_doctype: str,
	order_list: list,
	include_unallocated: bool = True,
) -> list:
	"""Return open advance journal entry rows matching the given party and orders."""
	journal_entry = frappe.qb.DocType("Journal Entry")
	journal_acc = frappe.qb.DocType("Journal Entry Account")
	q = (
		frappe.qb.from_(journal_entry)
		.inner_join(journal_acc)
		.on(journal_entry.name == journal_acc.parent)
		.select(
			ConstantColumn("Journal Entry").as_("reference_type"),
			(journal_entry.name).as_("reference_name"),
			(journal_entry.remark).as_("remarks"),
			(journal_acc[amount_field]).as_("amount"),
			(journal_acc.name).as_("reference_row"),
			(journal_acc.reference_name).as_("against_order"),
			(journal_acc.exchange_rate),
		)
		.where(
			journal_acc.account.isin(party_account)
			& (journal_acc.party_type == party_type)
			& (journal_acc.party == party)
			& (journal_acc.is_advance == "Yes")
			& (journal_entry.docstatus == 1)
		)
	)
	if party_type == "Customer":
		q = q.where(journal_acc.credit_in_account_currency > 0)
	else:
		q = q.where(journal_acc.debit_in_account_currency > 0)

	reference_or_condition = []

	if include_unallocated:
		reference_or_condition.append(journal_acc.reference_name.isnull())
		reference_or_condition.append(journal_acc.reference_name == "")

	if order_list:
		reference_or_condition.append(
			(journal_acc.reference_type == order_doctype) & ((journal_acc.reference_name).isin(order_list))
		)

	if reference_or_condition:
		q = q.where(Criterion.any(reference_or_condition))

	q = q.orderby(journal_entry.posting_date)

	return list(q.run(as_dict=True))


@erpnext.allow_regional
def get_advance_payment_entries_for_regional(*args, **kwargs):
	return get_advance_payment_entries(*args, **kwargs)


def get_advance_payment_entries(
	party_type: str,
	party: str,
	party_account: list,
	order_doctype: str,
	order_list: list | None = None,
	default_advance_account: str | None = None,
	include_unallocated: bool = True,
	against_all_orders: bool = False,
	limit: int | None = None,
	condition: dict | None = None,
) -> list:
	"""Return open advance payment entry rows matching the given party and orders."""
	payment_entries = []
	payment_entry = frappe.qb.DocType("Payment Entry")

	if order_list or against_all_orders:
		q = get_common_query(party_type, party, party_account, default_advance_account, limit, condition)
		payment_ref = frappe.qb.DocType("Payment Entry Reference")

		q = q.inner_join(payment_ref).on(payment_entry.name == payment_ref.parent)
		q = q.select(
			(payment_ref.allocated_amount).as_("amount"),
			(payment_ref.name).as_("reference_row"),
			(payment_ref.reference_name).as_("against_order"),
			(payment_entry.book_advance_payments_in_separate_party_account),
		)

		q = q.where(payment_ref.reference_doctype == order_doctype)
		if order_list:
			q = q.where(payment_ref.reference_name.isin(order_list))

		payment_entries += list(q.run(as_dict=True))

	if include_unallocated:
		q = get_common_query(party_type, party, party_account, default_advance_account, limit, condition)
		q = q.select((payment_entry.unallocated_amount).as_("amount"))
		q = q.where(payment_entry.unallocated_amount > 0)

		payment_entries += list(q.run(as_dict=True))

	return payment_entries


def get_common_query(
	party_type: str,
	party: str,
	party_account: list,
	default_advance_account: str | None,
	limit: int | None,
	condition: dict | None,
):
	"""Build the base Payment Entry query shared by allocated and unallocated advance lookups."""
	account_type = frappe.db.get_value("Party Type", party_type, "account_type")
	payment_type = "Receive" if account_type == "Receivable" else "Pay"
	payment_entry = frappe.qb.DocType("Payment Entry")

	q = (
		frappe.qb.from_(payment_entry)
		.select(
			ConstantColumn("Payment Entry").as_("reference_type"),
			(payment_entry.name).as_("reference_name"),
			payment_entry.posting_date,
			(payment_entry.remarks).as_("remarks"),
			(payment_entry.book_advance_payments_in_separate_party_account),
		)
		.where(payment_entry.payment_type == payment_type)
		.where(payment_entry.party_type == party_type)
		.where(payment_entry.party == party)
		.where(payment_entry.docstatus == 1)
	)

	field = "paid_from" if payment_type == "Receive" else "paid_to"
	q = q.select((payment_entry[f"{field}_account_currency"]).as_("currency"))
	q = q.select(payment_entry[field])
	account_condition = payment_entry[field].isin(party_account)
	if default_advance_account:
		q = q.where(
			account_condition
			| (
				(payment_entry[field] == default_advance_account)
				& (payment_entry.book_advance_payments_in_separate_party_account == 1)
			)
		)
	else:
		q = q.where(account_condition)

	if payment_type == "Receive":
		q = q.select((payment_entry.source_exchange_rate).as_("exchange_rate"))
	else:
		q = q.select((payment_entry.target_exchange_rate).as_("exchange_rate"))

	if condition:
		common_filter_conditions = []
		common_filter_conditions.append(payment_entry.company == condition["company"])
		if condition.get("name", None):
			common_filter_conditions.append(payment_entry.name.like(f"%{condition.get('name')}%"))
		if condition.get("from_payment_date"):
			common_filter_conditions.append(payment_entry.posting_date.gte(condition["from_payment_date"]))
		if condition.get("to_payment_date"):
			common_filter_conditions.append(payment_entry.posting_date.lte(condition["to_payment_date"]))
		if condition.get("get_payments") is True:
			if condition.get("cost_center"):
				common_filter_conditions.append(payment_entry.cost_center == condition["cost_center"])
			if condition.get("accounting_dimensions"):
				for field, val in condition.get("accounting_dimensions").items():
					common_filter_conditions.append(payment_entry[field] == val)
			if condition.get("minimum_payment_amount"):
				common_filter_conditions.append(
					payment_entry.unallocated_amount.gte(condition["minimum_payment_amount"])
				)
			if condition.get("maximum_payment_amount"):
				common_filter_conditions.append(
					payment_entry.unallocated_amount.lte(condition["maximum_payment_amount"])
				)
		q = q.where(Criterion.all(common_filter_conditions))

	q = q.orderby(payment_entry.posting_date)
	q = q.limit(limit) if limit else q

	return q


def _set_je_amounts(entry, amount, default_amount=None, is_credit=True):
	if is_credit:
		entry.credit_in_account_currency = amount
		if default_amount is not None:
			entry.credit = default_amount
	else:
		entry.debit_in_account_currency = amount
		if default_amount is not None:
			entry.debit = default_amount
