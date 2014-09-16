# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.defaults import get_user_permissions
from frappe.utils import add_days
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
	elif account:
		party = frappe.db.get_value('Account', account, 'master_name')

	account_fieldname = "debit_to" if party_type=="Customer" else "credit_to"

	out = {
		party_type.lower(): party,
		account_fieldname : account,
		"due_date": get_due_date(posting_date, party, party_type, account, company)
	}
	return out

def get_party_account(company, party, party_type):
	if not company:
		frappe.throw(_("Please select company first."))

	if party:
		acc_head = frappe.db.get_value("Account", {"master_name":party,
			"master_type": party_type, "company": company})

		if not acc_head:
			create_party_account(party, party_type, company)

		return acc_head

def get_due_date(posting_date, party, party_type, account, company):
	"""Set Due Date = Posting Date + Credit Days"""
	due_date = None
	if posting_date:
		credit_days = 0
		if account:
			credit_days = frappe.db.get_value("Account", account, "credit_days")
		if party and not credit_days:
			credit_days = frappe.db.get_value(party_type, party, "credit_days")
		if company and not credit_days:
			credit_days = frappe.db.get_value("Company", company, "credit_days")

		due_date = add_days(posting_date, credit_days) if credit_days else posting_date

	return due_date

def create_party_account(party, party_type, company):
	if not company:
		frappe.throw(_("Company is required"))

	company_details = frappe.db.get_value("Company", company,
		["abbr", "receivables_group", "payables_group"], as_dict=True)
	if not frappe.db.exists("Account", (party.strip() + " - " + company_details.abbr)):
		parent_account = company_details.receivables_group \
			if party_type=="Customer" else company_details.payables_group
		if not parent_account:
			frappe.throw(_("Please enter Account Receivable/Payable group in company master"))

		# create
		account = frappe.get_doc({
			"doctype": "Account",
			'account_name': party,
			'parent_account': parent_account,
			'group_or_ledger':'Ledger',
			'company': company,
			'master_type': party_type,
			'master_name': party,
			"freeze_account": "No",
			"report_type": "Balance Sheet"
		}).insert(ignore_permissions=True)

		frappe.msgprint(_("Account Created: {0}").format(account.name))
