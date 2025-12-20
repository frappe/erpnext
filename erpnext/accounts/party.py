# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint, qb, scrub
from frappe.contacts.doctype.address.address import get_company_address, get_default_address
from frappe.core.doctype.user_permission.user_permission import get_permitted_documents
from frappe.model.utils import get_fetch_values
from frappe.query_builder.functions import Abs, Count, Date, Sum
from frappe.utils import (
	add_days,
	add_months,
	add_years,
	cint,
	cstr,
	date_diff,
	flt,
	formatdate,
	get_last_day,
	get_timestamp,
	getdate,
	nowdate,
)

import erpnext
from erpnext import get_company_currency
from erpnext.accounts.utils import get_fiscal_year
from erpnext.exceptions import InvalidAccountCurrency, PartyDisabled, PartyFrozen
from erpnext.utilities.regional import temporary_flag

try:
	from frappe.contacts.doctype.address.address import render_address as _render_address
except ImportError:
	# Older frappe versions where this function is not available
	from frappe.contacts.doctype.address.address import get_address_display as _render_address

PURCHASE_TRANSACTION_TYPES = {
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Receipt",
	"Purchase Invoice",
}
SALES_TRANSACTION_TYPES = {
	"Quotation",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
	"POS Invoice",
}
TRANSACTION_TYPES = PURCHASE_TRANSACTION_TYPES | SALES_TRANSACTION_TYPES


class DuplicatePartyAccountError(frappe.ValidationError):
	pass


@frappe.whitelist()
def get_party_details(
	party=None,
	account=None,
	party_type="Customer",
	company=None,
	posting_date=None,
	bill_date=None,
	price_list=None,
	currency=None,
	doctype=None,
	ignore_permissions=False,
	fetch_payment_terms_template=True,
	party_address=None,
	company_address=None,
	shipping_address=None,
	dispatch_address=None,
	pos_profile=None,
):
	if not party:
		return frappe._dict()
	if not frappe.db.exists(party_type, party):
		frappe.throw(_("{0}: {1} does not exists").format(party_type, party))
	return _get_party_details(
		party,
		account,
		party_type,
		company,
		posting_date,
		bill_date,
		price_list,
		currency,
		doctype,
		ignore_permissions,
		fetch_payment_terms_template,
		party_address,
		company_address,
		shipping_address,
		dispatch_address,
		pos_profile,
	)


def _get_party_details(
	party=None,
	account=None,
	party_type="Customer",
	company=None,
	posting_date=None,
	bill_date=None,
	price_list=None,
	currency=None,
	doctype=None,
	ignore_permissions=False,
	fetch_payment_terms_template=True,
	party_address=None,
	company_address=None,
	shipping_address=None,
	dispatch_address=None,
	pos_profile=None,
):
	party_details = frappe._dict(
		set_account_and_due_date(party, account, party_type, company, posting_date, bill_date, doctype)
	)
	party = party_details[party_type.lower()]
	party = frappe.get_doc(party_type, party)

	if not ignore_permissions:
		ptype = "select" if frappe.only_has_select_perm(party_type) else "read"
		frappe.has_permission(party_type, ptype, party, throw=True)

	currency = party.get("default_currency") or currency or get_company_currency(company)

	party_address, shipping_address = set_address_details(
		party_details,
		party,
		party_type,
		doctype,
		company,
		party_address,
		company_address,
		shipping_address,
		dispatch_address,
		ignore_permissions=ignore_permissions,
	)
	set_contact_details(party_details, party, party_type)
	set_other_values(party_details, party, party_type)
	set_price_list(party_details, party, party_type, price_list, pos_profile)

	tax_template = set_taxes(
		party.name,
		party_type,
		posting_date,
		company,
		customer_group=party_details.customer_group,
		supplier_group=party_details.supplier_group,
		tax_category=party_details.tax_category,
		billing_address=party_address,
		shipping_address=shipping_address,
	)

	if tax_template:
		party_details["taxes_and_charges"] = tax_template

	if cint(fetch_payment_terms_template):
		party_details["payment_terms_template"] = get_payment_terms_template(party.name, party_type, company)

	if not party_details.get("currency"):
		party_details["currency"] = currency

	# sales team
	if party_type == "Customer":
		party_details["sales_team"] = [
			{
				"sales_person": d.sales_person,
				"allocated_percentage": d.allocated_percentage or None,
				"commission_rate": d.commission_rate,
			}
			for d in party.get("sales_team")
		]

	# supplier tax withholding category
	if party_type == "Supplier" and party:
		party_details["supplier_tds"] = frappe.get_value(party_type, party.name, "tax_withholding_category")

	if not party_details.get("tax_category") and pos_profile:
		party_details["tax_category"] = frappe.get_value("POS Profile", pos_profile, "tax_category")

	return party_details


def set_address_details(
	party_details,
	party,
	party_type,
	doctype=None,
	company=None,
	party_address=None,
	company_address=None,
	shipping_address=None,
	dispatch_address=None,
	*,
	ignore_permissions=False,
):
	# party_billing
	party_billing_field = (
		"customer_address" if party_type in ["Lead", "Prospect"] else party_type.lower() + "_address"
	)

	party_details[party_billing_field] = party_address or get_default_address(party_type, party.name)
	if doctype:
		party_details.update(
			get_fetch_values(doctype, party_billing_field, party_details[party_billing_field])
		)

	party_details.address_display = render_address(
		party_details[party_billing_field], check_permissions=not ignore_permissions
	)

	# party_shipping
	if party_type in ["Customer", "Lead"]:
		party_shipping_field = "shipping_address_name"
		party_shipping_display = "shipping_address"
		default_shipping = shipping_address

	else:
		# Supplier
		party_shipping_field = "dispatch_address"
		party_shipping_display = "dispatch_address_display"
		default_shipping = dispatch_address

	party_details[party_shipping_field] = default_shipping or get_party_shipping_address(
		party_type, party.name
	)

	party_details[party_shipping_display] = render_address(
		party_details[party_shipping_field], check_permissions=not ignore_permissions
	)

	if doctype:
		party_details.update(
			get_fetch_values(doctype, party_shipping_field, party_details[party_shipping_field])
		)

	# company_address
	if company_address:
		party_details.company_address = company_address
	else:
		party_details.update(get_company_address(company))

	if doctype in SALES_TRANSACTION_TYPES and party_details.company_address:
		party_details.update(get_fetch_values(doctype, "company_address", party_details.company_address))

	if doctype in PURCHASE_TRANSACTION_TYPES:
		if shipping_address:
			party_details.update(
				shipping_address=shipping_address,
				shipping_address_display=render_address(
					shipping_address, check_permissions=not ignore_permissions
				),
				**get_fetch_values(doctype, "shipping_address", shipping_address),
			)

		if party_details.company_address:
			# billing address
			party_details.update(
				billing_address=party_details.company_address,
				billing_address_display=(
					party_details.company_address_display
					or render_address(party_details.company_address, check_permissions=False)
				),
				**get_fetch_values(doctype, "billing_address", party_details.company_address),
			)

			# shipping address - if not already set
			if not party_details.shipping_address:
				party_details.update(
					shipping_address=party_details.billing_address,
					shipping_address_display=party_details.billing_address_display,
					**get_fetch_values(doctype, "shipping_address", party_details.billing_address),
				)

	party_billing, party_shipping = (
		party_details.get(party_billing_field),
		party_details.get(party_shipping_field),
	)

	party_details["tax_category"] = get_address_tax_category(
		party.get("tax_category"), party_billing, party_shipping
	)

	if doctype in TRANSACTION_TYPES:
		with temporary_flag("company", company):
			get_regional_address_details(party_details, doctype, company)

	return party_billing, party_shipping


@erpnext.allow_regional
def get_regional_address_details(party_details, doctype, company):
	pass


def complete_contact_details(party_details):
	contact_details = frappe._dict()

	if party_details.party_type == "Employee":
		contact_details = frappe.db.get_value(
			"Employee",
			party_details.party,
			[
				"employee_name as contact_display",
				"prefered_email as contact_email",
				"cell_number as contact_mobile",
				"designation as contact_designation",
				"department as contact_department",
			],
			as_dict=True,
		)

		contact_details.update({"contact_person": None, "contact_phone": None})
	elif party_details.contact_person:
		contact_details = frappe.db.get_value(
			"Contact",
			party_details.contact_person,
			[
				"name as contact_person",
				"full_name as contact_display",
				"email_id as contact_email",
				"mobile_no as contact_mobile",
				"phone as contact_phone",
				"designation as contact_designation",
				"department as contact_department",
			],
			as_dict=True,
		)
	else:
		contact_details = {
			"contact_person": None,
			"contact_display": None,
			"contact_email": None,
			"contact_mobile": None,
			"contact_phone": None,
			"contact_designation": None,
			"contact_department": None,
		}

	party_details.update(contact_details)


def set_contact_details(party_details, party, party_type):
	party_details.contact_person = get_default_contact(party_type, party.name)
	complete_contact_details(party_details)


def set_other_values(party_details, party, party_type):
	# copy
	if party_type == "Customer":
		to_copy = ["customer_name", "customer_group", "territory", "language"]
	else:
		to_copy = ["supplier_name", "supplier_group", "language"]
	for f in to_copy:
		party_details[f] = party.get(f)

	# fields prepended with default in Customer doctype
	for f in ["currency"] + (["sales_partner", "commission_rate"] if party_type == "Customer" else []):
		if party.get("default_" + f):
			party_details[f] = party.get("default_" + f)


def get_default_price_list(party):
	"""Return default price list for party (Document object)"""
	if party.get("default_price_list"):
		return party.default_price_list

	if party.doctype == "Customer":
		return frappe.get_cached_value("Customer Group", party.customer_group, "default_price_list")


def set_price_list(party_details, party, party_type, given_price_list, pos=None):
	# price list
	price_list = get_permitted_documents("Price List")

	# if there is only one permitted document based on user permissions, set it
	if price_list and len(price_list) == 1:
		price_list = price_list[0]
	elif pos and party_type == "Customer":
		customer_price_list = frappe.get_value("Customer", party.name, "default_price_list")

		if customer_price_list:
			price_list = customer_price_list
		else:
			pos_price_list = frappe.get_value("POS Profile", pos, "selling_price_list")
			price_list = pos_price_list or given_price_list
	else:
		price_list = get_default_price_list(party) or given_price_list

	if price_list:
		party_details.price_list_currency = frappe.db.get_value(
			"Price List", price_list, "currency", cache=True
		)

	party_details["selling_price_list" if party.doctype == "Customer" else "buying_price_list"] = price_list


def set_account_and_due_date(party, account, party_type, company, posting_date, bill_date, doctype):
	if doctype not in ["POS Invoice", "Sales Invoice", "Purchase Invoice"]:
		# not an invoice
		return {party_type.lower(): party}

	if party:
		account = get_party_account(party_type, party, company)

	account_fieldname = "debit_to" if party_type == "Customer" else "credit_to"
	out = {
		party_type.lower(): party,
		account_fieldname: account,
		"due_date": get_due_date(posting_date, party_type, party, company, bill_date),
	}

	return out


@frappe.whitelist()
def get_party_account(party_type, party=None, company=None, include_advance=False):
	"""Returns the account for the given `party`.
	Will first search in party (Customer / Supplier) record, if not found,
	will search in group (Customer Group / Supplier Group),
	finally will return default."""
	if not party_type:
		frappe.throw(_("Party Type is mandatory"))
	if not company:
		frappe.throw(_("Please select a Company"))

	if not party and party_type in ["Customer", "Supplier"]:
		default_account_name = (
			"default_receivable_account" if party_type == "Customer" else "default_payable_account"
		)

		return frappe.get_cached_value("Company", company, default_account_name)

	account = frappe.db.get_value(
		"Party Account", {"parenttype": party_type, "parent": party, "company": company}, "account"
	)

	if not account and party_type in ["Customer", "Supplier"]:
		party_group_doctype = "Customer Group" if party_type == "Customer" else "Supplier Group"
		group = frappe.get_cached_value(party_type, party, scrub(party_group_doctype))
		account = frappe.db.get_value(
			"Party Account",
			{"parenttype": party_group_doctype, "parent": group, "company": company},
			"account",
		)

	if not account and party_type in ["Customer", "Supplier"]:
		default_account_name = (
			"default_receivable_account" if party_type == "Customer" else "default_payable_account"
		)
		account = frappe.get_cached_value("Company", company, default_account_name)

	existing_gle_currency = get_party_gle_currency(party_type, party, company)
	if existing_gle_currency:
		if account:
			account_currency = frappe.get_cached_value("Account", account, "account_currency")
		if (account and account_currency != existing_gle_currency) or not account:
			account = get_party_gle_account(party_type, party, company)

	# get default account on the basis of party type
	if not account:
		account_type = frappe.get_cached_value("Party Type", party_type, "account_type")
		default_account_name = "default_" + account_type.lower() + "_account"
		account = frappe.get_cached_value("Company", company, default_account_name)

	if include_advance and party_type in ["Customer", "Supplier", "Student"]:
		advance_account = get_party_advance_account(party_type, party, company)
		if advance_account:
			return [account, advance_account]
		else:
			return [account]

	return account


def get_party_advance_account(party_type, party, company):
	account = frappe.db.get_value(
		"Party Account",
		{"parenttype": party_type, "parent": party, "company": company},
		"advance_account",
	)

	if not account:
		party_group_doctype = "Customer Group" if party_type == "Customer" else "Supplier Group"
		group = frappe.get_cached_value(party_type, party, scrub(party_group_doctype))
		account = frappe.db.get_value(
			"Party Account",
			{"parenttype": party_group_doctype, "parent": group, "company": company},
			"advance_account",
		)

	if not account:
		account_name = (
			"default_advance_received_account" if party_type == "Customer" else "default_advance_paid_account"
		)
		account = frappe.get_cached_value("Company", company, account_name)

	return account


@frappe.whitelist()
def get_party_bank_account(party_type, party):
	return frappe.db.get_value("Bank Account", {"party_type": party_type, "party": party, "is_default": 1})


def get_party_account_currency(party_type, party, company):
	def generator():
		party_account = get_party_account(party_type, party, company)
		return frappe.get_cached_value("Account", party_account, "account_currency")

	return frappe.local_cache("party_account_currency", (party_type, party, company), generator)


def get_party_gle_currency(party_type, party, company):
	def generator():
		gl = qb.DocType("GL Entry")
		existing_gle_currency = (
			qb.from_(gl)
			.select(gl.account_currency)
			.where(
				(gl.docstatus == 1)
				& (gl.company == company)
				& (gl.party_type == party_type)
				& (gl.party == party)
				& (gl.is_cancelled == 0)
			)
			.limit(1)
			.run()
		)

		return existing_gle_currency[0][0] if existing_gle_currency else None

	return frappe.local_cache(
		"party_gle_currency", (party_type, party, company), generator, regenerate_if_none=True
	)


def get_party_gle_account(party_type, party, company):
	def generator():
		existing_gle_account = frappe.db.sql(
			"""select account from `tabGL Entry`
			where docstatus=1 and company=%(company)s and party_type=%(party_type)s and party=%(party)s
			limit 1""",
			{"company": company, "party_type": party_type, "party": party},
		)

		return existing_gle_account[0][0] if existing_gle_account else None

	return frappe.local_cache(
		"party_gle_account", (party_type, party, company), generator, regenerate_if_none=True
	)


def validate_party_gle_currency(party_type, party, company, party_account_currency=None):
	"""Validate party account currency with existing GL Entry's currency"""
	if not party_account_currency:
		party_account_currency = get_party_account_currency(party_type, party, company)

	existing_gle_currency = get_party_gle_currency(party_type, party, company)

	if existing_gle_currency and party_account_currency != existing_gle_currency:
		frappe.throw(
			_(
				"{0} {1} has accounting entries in currency {2} for company {3}. Please select a receivable or payable account with currency {2}."
			).format(
				frappe.bold(party_type),
				frappe.bold(party),
				frappe.bold(existing_gle_currency),
				frappe.bold(company),
			),
			InvalidAccountCurrency,
		)


def validate_party_accounts(doc):
	from erpnext.controllers.accounts_controller import validate_account_head

	companies = []

	for account in doc.get("accounts"):
		if account.company in companies:
			frappe.throw(
				_("There can only be 1 Account per Company in {0} {1}").format(doc.doctype, doc.name),
				DuplicatePartyAccountError,
			)
		else:
			companies.append(account.company)

		party_account_currency = frappe.get_cached_value("Account", account.account, "account_currency")
		if frappe.db.get_default("Company"):
			company_default_currency = frappe.get_cached_value(
				"Company", frappe.db.get_default("Company"), "default_currency"
			)
		else:
			company_default_currency = frappe.get_cached_value("Company", account.company, "default_currency")

		validate_party_gle_currency(doc.doctype, doc.name, account.company, party_account_currency)

		if doc.get("default_currency") and party_account_currency and company_default_currency:
			if (
				doc.default_currency != party_account_currency
				and doc.default_currency != company_default_currency
			):
				frappe.throw(
					_(
						"Billing currency must be equal to either default company's currency or party account currency"
					)
				)

		# validate if account is mapped for same company
		if account.account:
			validate_account_head(account.idx, account.account, account.company, _("Debtor/Creditor"))
		if account.advance_account:
			validate_account_head(
				account.idx, account.advance_account, account.company, _("Debtor/Creditor Advance")
			)


@frappe.whitelist()
def get_due_date(posting_date, party_type, party, company=None, bill_date=None, template_name=None):
	"""Get due date from `Payment Terms Template`"""
	due_date = None
	if (bill_date or posting_date) and party:
		due_date = bill_date or posting_date
		if not template_name:
			template_name = get_payment_terms_template(party, party_type, company)

		if template_name:
			due_date = get_due_date_from_template(template_name, posting_date, bill_date).strftime("%Y-%m-%d")
		else:
			if party_type == "Supplier":
				supplier_group = frappe.get_cached_value(party_type, party, "supplier_group")
				template_name = frappe.get_cached_value("Supplier Group", supplier_group, "payment_terms")
				if template_name:
					due_date = get_due_date_from_template(template_name, posting_date, bill_date).strftime(
						"%Y-%m-%d"
					)
	# If due date is calculated from bill_date, check this condition
	if getdate(due_date) < getdate(posting_date):
		due_date = posting_date
	return due_date


def get_due_date_from_template(template_name, posting_date, bill_date):
	"""
	Inspects all `Payment Term`s from the a `Payment Terms Template` and returns the due
	date after considering all the `Payment Term`s requirements.
	:param template_name: Name of the `Payment Terms Template`
	:return: String representing the calculated due date
	"""
	due_date = getdate(bill_date or posting_date)

	template = frappe.get_doc("Payment Terms Template", template_name)

	for term in template.terms:
		if term.due_date_based_on == "Day(s) after invoice date":
			due_date = max(due_date, add_days(due_date, term.credit_days))
		elif term.due_date_based_on == "Day(s) after the end of the invoice month":
			due_date = max(due_date, add_days(get_last_day(due_date), term.credit_days))
		else:
			due_date = max(due_date, get_last_day(add_months(due_date, term.credit_months)))
	return due_date


def validate_due_date(posting_date, due_date, bill_date=None, template_name=None, doctype=None):
	if getdate(due_date) < getdate(posting_date):
		doctype_date = "Date"
		if doctype == "Purchase Invoice":
			doctype_date = "Supplier Invoice Date"

		if doctype == "Sales Invoice":
			doctype_date = "Posting Date"

		frappe.throw(_("Due Date cannot be before {0}").format(doctype_date))
	else:
		validate_due_date_with_template(posting_date, due_date, bill_date, template_name, doctype)


def validate_due_date_with_template(posting_date, due_date, bill_date, template_name, doctype=None):
	if not template_name:
		return

	default_due_date = format(get_due_date_from_template(template_name, posting_date, bill_date))

	if not default_due_date:
		return

	if default_due_date != posting_date and getdate(due_date) > getdate(default_due_date):
		if frappe.get_single_value("Accounts Settings", "credit_controller") in frappe.get_roles():
			party_type = "supplier" if doctype == "Purchase Invoice" else "customer"

			msgprint(
				_("Note: Due Date exceeds allowed {0} credit days by {1} day(s)").format(
					party_type, date_diff(due_date, default_due_date)
				)
			)
		else:
			frappe.throw(_("Due Date cannot be after {0}").format(formatdate(default_due_date)))


@frappe.whitelist()
def get_address_tax_category(tax_category=None, billing_address=None, shipping_address=None):
	addr_tax_category_from = frappe.get_single_value(
		"Accounts Settings", "determine_address_tax_category_from"
	)
	if addr_tax_category_from == "Shipping Address":
		if shipping_address:
			tax_category = frappe.db.get_value("Address", shipping_address, "tax_category") or tax_category
	else:
		if billing_address:
			tax_category = frappe.db.get_value("Address", billing_address, "tax_category") or tax_category

	return cstr(tax_category)


@frappe.whitelist()
def set_taxes(
	party,
	party_type,
	posting_date,
	company,
	customer_group=None,
	supplier_group=None,
	tax_category=None,
	billing_address=None,
	shipping_address=None,
	use_for_shopping_cart=None,
):
	from erpnext.accounts.doctype.tax_rule.tax_rule import get_party_details, get_tax_template

	args = {frappe.scrub(party_type): party, "company": company}

	if tax_category:
		args["tax_category"] = tax_category

	if customer_group:
		args["customer_group"] = customer_group

	if supplier_group:
		args["supplier_group"] = supplier_group

	if billing_address or shipping_address:
		args.update(
			get_party_details(
				party, party_type, {"billing_address": billing_address, "shipping_address": shipping_address}
			)
		)
	else:
		args.update(get_party_details(party, party_type))

	if party_type in ("Customer", "Lead", "Prospect", "CRM Deal"):
		args.update({"tax_type": "Sales"})

		if party_type in ["Lead", "Prospect", "CRM Deal"]:
			args["customer"] = None
			del args[frappe.scrub(party_type)]
	else:
		args.update({"tax_type": "Purchase"})

	if use_for_shopping_cart:
		args.update({"use_for_shopping_cart": use_for_shopping_cart})

	return get_tax_template(posting_date, args)


@frappe.whitelist()
def get_payment_terms_template(party_name, party_type, company=None):
	if party_type not in ("Customer", "Supplier"):
		return
	template = None

	if party_type == "Customer":
		customer = frappe.get_cached_value(
			"Customer", party_name, fieldname=["payment_terms", "customer_group"], as_dict=1
		)
		template = customer.payment_terms

		if not template and customer.customer_group:
			template = frappe.get_cached_value("Customer Group", customer.customer_group, "payment_terms")
	else:
		supplier = frappe.get_cached_value(
			"Supplier", party_name, fieldname=["payment_terms", "supplier_group"], as_dict=1
		)
		template = supplier.payment_terms
		if not template and supplier.supplier_group:
			template = frappe.get_cached_value("Supplier Group", supplier.supplier_group, "payment_terms")

	if not template and company:
		template = frappe.get_cached_value("Company", company, fieldname="payment_terms")
	return template


def validate_party_frozen_disabled(company, party_type, party_name):
	if frappe.flags.ignore_party_validation:
		return

	if party_type and party_name:
		if party_type in ("Customer", "Supplier"):
			party = frappe.get_cached_value(party_type, party_name, ["is_frozen", "disabled"], as_dict=True)
			if party.disabled:
				frappe.throw(_("{0} {1} is disabled").format(party_type, party_name), PartyDisabled)
			elif party.get("is_frozen"):
				role_allowed_for_frozen_entries = frappe.get_cached_value(
					"Company", company, "role_allowed_for_frozen_entries"
				)
				if role_allowed_for_frozen_entries not in frappe.get_roles():
					frappe.throw(_("{0} {1} is frozen").format(party_type, party_name), PartyFrozen)

		elif party_type == "Employee":
			if frappe.db.get_value("Employee", party_name, "status") != "Active":
				frappe.msgprint(_("{0} {1} is not active").format(party_type, party_name), alert=True)


def validate_account_party_type(self):
	if self.is_cancelled:
		return

	if self.party_type and self.party:
		account_type = frappe.get_cached_value("Account", self.account, "account_type")
		if account_type and (account_type not in ["Receivable", "Payable", "Equity"]):
			frappe.throw(
				_("Party Type and Party can only be set for Receivable / Payable account<br><br>{0}").format(
					self.account
				)
			)


def get_dashboard_info(party_type, party, loyalty_program=None):
	current_fiscal_year = get_fiscal_year(nowdate(), as_dict=True)

	doctype = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"

	companies = frappe.get_all(
		doctype, filters={"docstatus": 1, party_type.lower(): party}, distinct=1, fields=["company"]
	)

	company_wise_info = []

	company_wise_grand_total = frappe.get_all(
		doctype,
		filters={
			"docstatus": 1,
			party_type.lower(): party,
			"posting_date": (
				"between",
				[current_fiscal_year.year_start_date, current_fiscal_year.year_end_date],
			),
		},
		group_by="company",
		fields=[
			"company",
			{"SUM": "grand_total", "as": "grand_total"},
			{"SUM": "base_grand_total", "as": "base_grand_total"},
		],
	)

	loyalty_point_details = []

	if party_type == "Customer":
		loyalty_point_details = frappe._dict(
			frappe.get_all(
				"Loyalty Point Entry",
				filters={
					"customer": party,
					"expiry_date": (">=", getdate()),
				},
				group_by="company",
				fields=["company", {"SUM": "loyalty_points", "as": "loyalty_points"}],
				as_list=1,
			)
		)

	company_wise_billing_this_year = frappe._dict()

	for d in company_wise_grand_total:
		company_wise_billing_this_year.setdefault(
			d.company, {"grand_total": d.grand_total, "base_grand_total": d.base_grand_total}
		)

	company_wise_total_unpaid = frappe._dict(
		frappe.db.sql(
			"""
		select company, sum(debit_in_account_currency) - sum(credit_in_account_currency)
		from `tabGL Entry`
		where party_type = %s and party=%s
		and is_cancelled = 0
		group by company""",
			(party_type, party),
		)
	)

	for d in companies:
		company_default_currency = frappe.get_cached_value("Company", d.company, "default_currency")
		party_account_currency = get_party_account_currency(party_type, party, d.company)

		if party_account_currency == company_default_currency:
			billing_this_year = flt(company_wise_billing_this_year.get(d.company, {}).get("base_grand_total"))
		else:
			billing_this_year = flt(company_wise_billing_this_year.get(d.company, {}).get("grand_total"))

		total_unpaid = flt(company_wise_total_unpaid.get(d.company))

		if loyalty_point_details:
			loyalty_points = loyalty_point_details.get(d.company)

		info = {}
		info["billing_this_year"] = flt(billing_this_year) if billing_this_year else 0
		info["currency"] = party_account_currency
		info["total_unpaid"] = flt(total_unpaid) if total_unpaid else 0
		info["company"] = d.company

		if party_type == "Customer" and loyalty_point_details:
			info["loyalty_points"] = loyalty_points

		if party_type == "Supplier":
			info["total_unpaid"] = -1 * info["total_unpaid"]

		company_wise_info.append(info)

	return company_wise_info


def get_party_shipping_address(doctype: str, name: str) -> str | None:
	"""
	Returns an Address name (best guess) for the given doctype and name for which `address_type == 'Shipping'` is true.
	and/or `is_shipping_address = 1`.

	It returns an empty string if there is no matching record.

	:param doctype: Party Doctype
	:param name: Party name
	:return: String
	"""
	shipping_addresses = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", doctype],
			["Dynamic Link", "link_name", "=", name],
			["disabled", "=", 0],
		],
		or_filters=[
			["is_shipping_address", "=", 1],
			["address_type", "=", "Shipping"],
		],
		fields=["name", "is_shipping_address"],
		order_by="is_shipping_address DESC",
	)

	if shipping_addresses and shipping_addresses[0].is_shipping_address == 1:
		return shipping_addresses[0].name
	if len(shipping_addresses) == 1:
		return shipping_addresses[0].name
	else:
		return None


def get_partywise_advanced_payment_amount(
	party_type, posting_date=None, future_payment=0, company=None, party=None
):
	account_type = frappe.get_cached_value("Party Type", party_type, "account_type")

	ple = frappe.qb.DocType("Payment Ledger Entry")
	acc = frappe.qb.DocType("Account")

	query = (
		frappe.qb.from_(ple)
		.inner_join(acc)
		.on(ple.account == acc.name)
		.select(ple.party)
		.where((ple.party_type.isin(party_type)) & (acc.account_type == account_type) & (ple.delinked == 0))
		.groupby(ple.party)
	)

	if posting_date:
		if future_payment:
			query = query.where((ple.posting_date <= posting_date) | (Date(ple.creation) <= posting_date))
		else:
			query = query.where(ple.posting_date <= posting_date)

	if company:
		query = query.where(ple.company == company)

	if party:
		query = query.where(ple.party == party)

	if invoice_doctypes := frappe.get_hooks("invoice_doctypes"):
		query = query.where(ple.voucher_type.notin(invoice_doctypes))

	# Get advance amount from Receivable / Payable Account
	party_ledger = query.select(Abs(Sum(ple.amount).as_("amount")))
	party_ledger = party_ledger.where(ple.amount < 0)
	party_ledger = party_ledger.where(ple.against_voucher_no == ple.voucher_no)
	party_ledger = party_ledger.where(
		acc.root_type == ("Liability" if account_type == "Payable" else "Asset")
	)

	data = party_ledger.run()
	data = frappe._dict(data or {})

	# Get advance amount from Advance Account
	advance_ledger = query.select(Sum(ple.amount).as_("amount"), ple.account)
	advance_ledger = advance_ledger.where(
		acc.root_type == ("Asset" if account_type == "Payable" else "Liability")
	)
	advance_ledger = advance_ledger.groupby(ple.account)
	advance_ledger = advance_ledger.having(Sum(ple.amount) < 0)

	advance_data = advance_ledger.run()

	for row in advance_data:
		data.setdefault(row[0], 0)
		data[row[0]] += abs(row[1])

	return data


def get_default_contact(doctype: str, name: str) -> str | None:
	"""
	Returns contact name only if there is a primary contact for given doctype and name.

	Else returns None

	:param doctype: Party Doctype
	:param name: Party name
	:return: String
	"""
	contacts = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", doctype],
			["Dynamic Link", "link_name", "=", name],
		],
		or_filters=[
			["is_primary_contact", "=", 1],
			["is_billing_contact", "=", 1],
		],
		pluck="name",
		limit=1,
		order_by="is_primary_contact DESC, is_billing_contact DESC",
	)

	return contacts[0] if contacts else None


def add_party_account(party_type, party, company, account):
	doc = frappe.get_doc(party_type, party)
	account_exists = False
	for d in doc.get("accounts"):
		if d.account == account:
			account_exists = True

	if not account_exists:
		accounts = {"company": company, "account": account}

		doc.append("accounts", accounts)

		doc.save()


def render_address(address, check_permissions=True):
	return frappe.call(_render_address, address, check_permissions=check_permissions)
