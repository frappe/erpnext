# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_url

def create_payment_gateway_and_account(gateway):
	"""If ERPNext is installed, create Payment Gateway and Payment Gateway Account"""
	if "erpnext" not in frappe.get_installed_apps():
		return

	create_payment_gateway(gateway)
	create_payment_gateway_account(gateway)

def create_payment_gateway(gateway):
	# NOTE: we don't translate Payment Gateway name because it is an internal doctype
	if not frappe.db.exists("Payment Gateway", gateway):
		payment_gateway = frappe.get_doc({
			"doctype": "Payment Gateway",
			"gateway": gateway
		})
		payment_gateway.insert(ignore_permissions=True)

def create_payment_gateway_account(gateway):
	from erpnext.setup.setup_wizard.setup_wizard import create_bank_account

	company = frappe.db.get_value("Global Defaults", None, "default_company")
	if not company:
		return

	# NOTE: we translate Payment Gateway account name because that is going to be used by the end user
	bank_account = frappe.db.get_value("Account", {"account_name": _(gateway), "company": company},
		["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# check for untranslated one
		bank_account = frappe.db.get_value("Account", {"account_name": gateway, "company": company},
			["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# try creating one
		bank_account = create_bank_account({"company_name": company, "bank_account": _(gateway)})

	if not bank_account:
		frappe.msgprint(_("Payment Gateway Account not created, please create one manually."))
		return

	# if payment gateway account exists, return
	if frappe.db.exists("Payment Gateway Account",
		{"payment_gateway": gateway, "currency": bank_account.account_currency}):
		return

	try:
		frappe.get_doc({
			"doctype": "Payment Gateway Account",
			"is_default": 1,
			"payment_gateway": gateway,
			"payment_account": bank_account.name,
			"currency": bank_account.account_currency
		}).insert(ignore_permissions=True)

	except frappe.DuplicateEntryError:
		# already exists, due to a reinstall?
		pass

def set_redirect(doc):
	if "erpnext" not in frappe.get_installed_apps():
		return

	if not doc.flags.status_changed_to:
		return

	reference_doctype = doc.reference_doctype
	reference_docname = doc.reference_docname

	if not (reference_doctype and reference_docname):
		return

	reference_doc = frappe.get_doc(reference_doctype,  reference_docname)
	shopping_cart_settings = frappe.get_doc("Shopping Cart Settings")

	if doc.flags.status_changed_to in ["Authorized", "Completed"]:
		reference_doc.run_method("set_as_paid")

		# if shopping cart enabled and in session
		if (shopping_cart_settings.enabled
			and hasattr(frappe.local, "session")
			and frappe.local.session.user != "Guest"):

			success_url = shopping_cart_settings.payment_success_url
			if success_url:
				doc.flags.redirect_to = ({
					"Orders": "orders",
					"Invoices": "invoices",
					"My Account": "me"
				}).get(success_url, "me")
			else:
				doc.flags.redirect_to = get_url("/orders/{0}".format(reference_doc.reference_name))

def validate_transaction_currency(supported_currencies, transaction_currency, service_name):
	if transaction_currency not in supported_currencies:
		frappe.throw(_("Please select another payment method. {0} does not support transactions in currency '{1}'").format(service_name, transaction_currency))
