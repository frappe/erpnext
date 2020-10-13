# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe import _
from frappe.utils import flt, has_common
from frappe.utils.user import is_website_user

def get_list_context(context=None):
	return {
		"global_number_format": frappe.db.get_default("number_format") or "#,###.##",
		"currency": frappe.db.get_default("currency"),
		"currency_symbols": json.dumps(dict(frappe.db.sql("""select name, symbol
			from tabCurrency where enabled=1"""))),
		"row_template": "templates/includes/transaction_row.html",
		"get_list": get_transaction_list
	}


def get_transaction_list(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by="modified"):
	user = frappe.session.user
	ignore_permissions = False

	if not filters: filters = []

	if doctype in ['Supplier Quotation', 'Purchase Invoice', 'Quotation']:
		filters.append((doctype, 'docstatus', '<', 2))
	else:
		filters.append((doctype, 'docstatus', '=', 1))

	if (user != 'Guest' and is_website_user()) or doctype == 'Request for Quotation':
		parties_doctype = 'Request for Quotation Supplier' if doctype == 'Request for Quotation' else doctype
		# find party for this contact
		customers, suppliers = get_customers_suppliers(parties_doctype, user)

		if customers:
			if doctype == 'Quotation':
				filters.append(('quotation_to', '=', 'Customer'))
				filters.append(('party_name', 'in', customers))
			else:
				filters.append(('customer', 'in', customers))
		elif suppliers:
			filters.append(('supplier', 'in', suppliers))
		else:
			return []

		if doctype == 'Request for Quotation':
			parties = customers or suppliers
			return rfq_transaction_list(parties_doctype, doctype, parties, limit_start, limit_page_length)

		# Since customers and supplier do not have direct access to internal doctypes
		ignore_permissions = True

	transactions = get_list_for_transactions(doctype, txt, filters, limit_start, limit_page_length,
		fields='name', ignore_permissions=ignore_permissions, order_by='modified desc')

	return post_process(doctype, transactions)

def get_list_for_transactions(doctype, txt, filters, limit_start, limit_page_length=20,
	ignore_permissions=False, fields=None, order_by=None):
	""" Get List of transactions like Invoices, Orders """
	from frappe.www.list import get_list
	meta = frappe.get_meta(doctype)
	data = []
	or_filters = []

	for d in get_list(doctype, txt, filters=filters, fields="name", limit_start=limit_start,
		limit_page_length=limit_page_length, ignore_permissions=ignore_permissions, order_by="modified desc"):
		data.append(d)

	if txt:
		if meta.get_field('items'):
			if meta.get_field('items').options:
				child_doctype = meta.get_field('items').options
				for item in frappe.get_all(child_doctype, {"item_name": ['like', "%" + txt + "%"]}):
					child = frappe.get_doc(child_doctype, item.name)
					or_filters.append([doctype, "name", "=", child.parent])

	if or_filters:
		for r in frappe.get_list(doctype, fields=fields,filters=filters, or_filters=or_filters,
			limit_start=limit_start, limit_page_length=limit_page_length,
			ignore_permissions=ignore_permissions, order_by=order_by):
			data.append(r)

	return data

def rfq_transaction_list(parties_doctype, doctype, parties, limit_start, limit_page_length):
	data = frappe.db.sql("""select distinct parent as name, supplier from `tab{doctype}`
			where supplier = '{supplier}' and docstatus=1  order by modified desc limit {start}, {len}""".
			format(doctype=parties_doctype, supplier=parties[0], start=limit_start, len = limit_page_length), as_dict=1)

	return post_process(doctype, data)

def post_process(doctype, data):
	result = []
	for d in data:
		doc = frappe.get_doc(doctype, d.name)

		doc.status_percent = 0
		doc.status_display = []

		if doc.get("per_billed"):
			doc.status_percent += flt(doc.per_billed)
			doc.status_display.append(_("Billed") if doc.per_billed==100 else _("{0}% Billed").format(doc.per_billed))

		if doc.get("per_delivered"):
			doc.status_percent += flt(doc.per_delivered)
			doc.status_display.append(_("Delivered") if doc.per_delivered==100 else _("{0}% Delivered").format(doc.per_delivered))

		if hasattr(doc, "set_indicator"):
			doc.set_indicator()

		doc.status_display = ", ".join(doc.status_display)
		doc.items_preview = ", ".join([d.item_name for d in doc.items if d.item_name])
		result.append(doc)

	return result

def get_customers_suppliers(doctype, user):
	customers = []
	suppliers = []
	meta = frappe.get_meta(doctype)

	customer_field_name = get_customer_field_name(doctype)

	has_customer_field = meta.has_field(customer_field_name)
	has_supplier_field = meta.has_field('supplier')

	if has_common(["Supplier", "Customer"], frappe.get_roles(user)):
		contacts = frappe.db.sql("""
			select
				`tabContact`.email_id,
				`tabDynamic Link`.link_doctype,
				`tabDynamic Link`.link_name
			from
				`tabContact`, `tabDynamic Link`
			where
				`tabContact`.name=`tabDynamic Link`.parent and `tabContact`.email_id =%s
			""", user, as_dict=1)
		customers = [c.link_name for c in contacts if c.link_doctype == 'Customer']
		suppliers = [c.link_name for c in contacts if c.link_doctype == 'Supplier']
	elif frappe.has_permission(doctype, 'read', user=user):
		customer_list = frappe.get_list("Customer")
		customers = suppliers = [customer.name for customer in customer_list]

	return customers if has_customer_field else None, \
		suppliers if has_supplier_field else None

def has_website_permission(doc, ptype, user, verbose=False):
	doctype = doc.doctype
	customers, suppliers = get_customers_suppliers(doctype, user)
	if customers:
		return frappe.db.exists(doctype, get_customer_filter(doc, customers))
	elif suppliers:
		fieldname = 'suppliers' if doctype == 'Request for Quotation' else 'supplier'
		return frappe.db.exists(doctype, {
			'name': doc.name,
			fieldname: ["in", suppliers]
		})
	else:
		return False

def get_customer_filter(doc, customers):
	doctype = doc.doctype
	filters = frappe._dict()
	filters.name = doc.name
	filters[get_customer_field_name(doctype)] = ['in', customers]
	if doctype == 'Quotation':
		filters.quotation_to = 'Customer'
	return filters

def get_customer_field_name(doctype):
	if doctype == 'Quotation':
		return 'party_name'
	else:
		return 'customer'
