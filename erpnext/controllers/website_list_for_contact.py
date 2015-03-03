# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.user import is_website_user

def get_list_context(context=None):
	return {
		"global_number_format": frappe.db.get_default("number_format") or "#,###.##",
		"currency": frappe.db.get_default("currency"),
		"currency_symbols": json.dumps(dict(frappe.db.sql("""select name, symbol
			from tabCurrency where ifnull(enabled,0)=1"""))),
		"row_template": "templates/includes/transaction_row.html",
		"get_list": get_transaction_list
	}

def get_transaction_list(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20):
	from frappe.templates.pages.list import get_list
	user = frappe.session.user

	if user != "Guest" and is_website_user(user):
		# find party for this contact
		customers, suppliers = get_customers_suppliers(doctype, user)
		if customers:
			return post_process(get_list(doctype, txt, filters=[(doctype, "customer", "in", customers)],
				limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True))

		elif suppliers:
			return post_process(get_list(doctype, txt, filters=[(doctype, "supplier", "in", suppliers)],
				limit_start=limit_start, limit_page_length=limit_page_length, ignore_permissions=True))

		else:
			return []

	return post_process(get_list(doctype, txt, filters, limit_start, limit_page_length))

def post_process(result):
	for r in result:
		r.status_percent = 0
		r.status_display = []

		if r.get("per_billed"):
			r.status_percent += flt(r.per_billed)
			r.status_display.append(_("Billed") if r.per_billed==100 else _("{0}% Billed").format(r.per_billed))

		if r.get("per_delivered"):
			r.status_percent += flt(r.per_delivered)
			r.status_display.append(_("Delivered") if r.per_delivered==100 else _("{0}% Delivered").format(r.per_delivered))

		r.status_display = ", ".join(r.status_display)

	return result

def get_customers_suppliers(doctype, user):
	meta = frappe.get_meta(doctype)
	contacts = frappe.get_all("Contact", fields=["customer", "supplier", "email_id"],
		filters={"email_id": user})

	customers = [c.customer for c in contacts if c.customer] if meta.get_field("customer") else None
	suppliers = [c.supplier for c in contacts if c.supplier] if meta.get_field("supplier") else None

	return customers, suppliers

def has_website_permission(doc, ptype, user, verbose=False):
	doctype = doc.doctype
	customers, suppliers = get_customers_suppliers(doctype, user)
	if customers:
		return frappe.get_all(doctype, filters=[(doctype, "customer", "in", customers),
			(doctype, "name", "=", doc.name)]) and True or False
	elif suppliers:
		return frappe.get_all(doctype, filters=[(doctype, "suppliers", "in", suppliers),
			(doctype, "name", "=", doc.name)]) and True or False
	else:
		return False
