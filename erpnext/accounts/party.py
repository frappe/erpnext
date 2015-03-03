# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, msgprint, scrub
from frappe.defaults import get_user_permissions
from frappe.utils import add_days, getdate, formatdate, flt
from erpnext.utilities.doctype.address.address import get_address_display
from erpnext.utilities.doctype.contact.contact import get_contact_details

@frappe.whitelist()
def get_party_details(party=None, account=None, party_type="Customer", company=None,
	posting_date=None, price_list=None, currency=None, doctype=None):

	return _get_party_details(party, account, party_type,
		company, posting_date, price_list, currency, doctype)

def _get_party_details(party=None, account=None, party_type="Customer", company=None,
	posting_date=None, price_list=None, currency=None, doctype=None, ignore_permissions=False):
	out = frappe._dict(set_account_and_due_date(party, account, party_type, company, posting_date, doctype))

	party = out[party_type.lower()]

	if not ignore_permissions and not frappe.has_permission(party_type, "read", party):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	party = frappe.get_doc(party_type, party)

	set_address_details(out, party, party_type)
	set_contact_details(out, party, party_type)
	set_other_values(out, party, party_type)
	set_price_list(out, party, party_type, price_list)

	if not out.get("currency"):
		out["currency"] = currency

	# sales team
	if party_type=="Customer":
		out["sales_team"] = [{
			"sales_person": d.sales_person,
			"sales_designation": d.sales_designation,
			"allocated_percentage": d.allocated_percentage
		} for d in party.get("sales_team")]

	return out

def set_address_details(out, party, party_type):
	billing_address_field = "customer_address" if party_type == "Lead" \
		else party_type.lower() + "_address"
	out[billing_address_field] = frappe.db.get_value("Address",
		{party_type.lower(): party.name, "is_primary_address":1}, "name")

	# address display
	out.address_display = get_address_display(out[billing_address_field])

	# shipping address
	if party_type in ["Customer", "Lead"]:
		out.shipping_address_name = frappe.db.get_value("Address",
			{party_type.lower(): party.name, "is_shipping_address":1}, "name")
		out.shipping_address = get_address_display(out["shipping_address_name"])

def set_contact_details(out, party, party_type):
	out.contact_person = frappe.db.get_value("Contact",
		{party_type.lower(): party.name, "is_primary_contact":1}, "name")

	if not out.contact_person:
		return

	out.update(get_contact_details(out.contact_person))

def set_other_values(out, party, party_type):
	# copy
	if party_type=="Customer":
		to_copy = ["customer_name", "customer_group", "territory"]
	else:
		to_copy = ["supplier_name", "supplier_type"]
	for f in to_copy:
		out[f] = party.get(f)

	# fields prepended with default in Customer doctype
	for f in ['currency', 'taxes_and_charges'] \
		+ (['sales_partner', 'commission_rate'] if party_type=="Customer" else []):
		if party.get("default_" + f):
			out[f] = party.get("default_" + f)

def set_price_list(out, party, party_type, given_price_list):
	# price list
	price_list = filter(None, get_user_permissions().get("Price List", []))
	if isinstance(price_list, list):
		price_list = price_list[0] if len(price_list)==1 else None

	if not price_list:
		price_list = party.default_price_list

	if not price_list and party_type=="Customer":
		price_list =  frappe.db.get_value("Customer Group",
			party.customer_group, "default_price_list")

	if not price_list:
		price_list = given_price_list

	if price_list:
		out.price_list_currency = frappe.db.get_value("Price List", price_list, "currency")

	out["selling_price_list" if party.doctype=="Customer" else "buying_price_list"] = price_list


def set_account_and_due_date(party, account, party_type, company, posting_date, doctype):
	if doctype not in ["Sales Invoice", "Purchase Invoice"]:
		# not an invoice
		return {
			party_type.lower(): party
		}

	if party:
		account = get_party_account(company, party, party_type)

	account_fieldname = "debit_to" if party_type=="Customer" else "credit_to"

	out = {
		party_type.lower(): party,
		account_fieldname : account,
		"due_date": get_due_date(posting_date, party_type, party, company)
	}
	return out

@frappe.whitelist()
def get_party_account(company, party, party_type):
	"""Returns the account for the given `party`.
		Will first search in party (Customer / Supplier) record, if not found,
		will search in group (Customer Group / Supplier Type),
		finally will return default."""
	if not company:
		frappe.throw(_("Please select company first."))

	if party:
		account = frappe.db.get_value("Party Account",
			{"parenttype": party_type, "parent": party, "company": company}, "account")

		if not account:
			party_group_doctype = "Customer Group" if party_type=="Customer" else "Supplier Type"
			group = frappe.db.get_value(party_type, party, scrub(party_group_doctype))
			account = frappe.db.get_value("Party Account",
				{"parenttype": party_group_doctype, "parent": group, "company": company}, "account")

		if not account:
			default_account_name = "default_receivable_account" if party_type=="Customer" else "default_payable_account"
			account = frappe.db.get_value("Company", company, default_account_name)

		return account

def get_due_date(posting_date, party_type, party, company):
	"""Set Due Date = Posting Date + Credit Days"""
	due_date = None
	if posting_date:
		credit_days = get_credit_days(party_type, party, company)
		due_date = add_days(posting_date, credit_days) if credit_days else posting_date

	return due_date

def get_credit_days(party_type, party, company):
	party_group_doctype = "Customer Group" if party_type=="Customer" else "Supplier Type"
	credit_days, party_group = frappe.db.get_value(party_type, party, ["credit_days", frappe.scrub(party_group_doctype)])

	if not credit_days:
		credit_days = frappe.db.get_value(party_group_doctype, party_group, "credit_days") or \
			frappe.db.get_value("Company", company, "credit_days")

	return credit_days

def validate_due_date(posting_date, due_date, party_type, party, company):
	credit_days = get_credit_days(party_type, party, company)

	posting_date, due_date = getdate(posting_date), getdate(due_date)
	diff = (due_date - posting_date).days

	if diff < 0:
		frappe.throw(_("Due Date cannot be before Posting Date"))
	elif credit_days is not None and diff > flt(credit_days):
		is_credit_controller = frappe.db.get_value("Accounts Settings", None,
			"credit_controller") in frappe.user.get_roles()

		if is_credit_controller:
			msgprint(_("Note: Due / Reference Date exceeds allowed customer credit days by {0} day(s)")
				.format(diff - flt(credit_days)))
		else:
			max_due_date = formatdate(add_days(posting_date, credit_days))
			frappe.throw(_("Due / Reference Date cannot be after {0}").format(max_due_date))
