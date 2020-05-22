# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import operator
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


def get_transaction_list(doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by="not_implemented"):
	"""Returns a list of transactions for doctype 'doctype' based on contact-linked permissions.

	Arguments:
		doctype - DocType to query
		txt - Optional search string
		filters - Optional additional filters
		limit_start - Starting index of item when using limit_page_length (default 0)
		limit_page_length - Maximum number of items to return (default 20)
		order_by - Not implemented
	"""
	user = frappe.session.user
	ignore_permissions = False

	if not filters:
		filters = []
	customer_filters = []
	supplier_filters = []

	if doctype in ['Supplier Quotation', 'Purchase Invoice']:
		filters.append((doctype, 'docstatus', '<', 2))
	else:
		filters.append((doctype, 'docstatus', '=', 1))

	# If we have read access on this doctype, we return all results
	if frappe.has_permission(doctype, 'read', user):
		transactions = get_list_for_transactions(
			doctype, txt, filters, limit_start, limit_page_length, fields='name',
			ignore_permissions=True, order_by='modified desc')
		return post_process(doctype, transactions)

	# Otherwise, we limit results to ones linked by contacts or suppliers
	# Return empty list except for Request for Quotation
	if (user == 'Guest') and (doctype != 'Request for Quotation'):
		return []

	parties_doctype = 'Request for Quotation Supplier' if doctype == 'Request for Quotation' else doctype
	# find party for this contact
	customers, suppliers = get_customers_suppliers(parties_doctype, user)

	if not (customers or suppliers):
		# No customers or suppliers linked, so return empty list
		return []
	if customers:
		if doctype == 'Quotation':
			customer_filters.append(('quotation_to', '=', 'Customer'))
			customer_filters.append(('party_name', 'in', customers))
		else:
			customer_filters.append(('customer', 'in', customers))
	if suppliers:
		supplier_filters.append(('supplier', 'in', suppliers))

	# TODO - make this bit make sense
	if doctype == 'Request for Quotation':
		parties = customers or suppliers
		return rfq_transaction_list(parties, limit_start, limit_page_length)

	# Since customers and supplier do not have direct access to internal doctypes
	ignore_permissions = True

	transactions = []
	customer_doc_names = set()
	# If we are linked by customers or suppliers, then we search without getting permissions.
	if customers:
		# Get transactions linked by Customer
		transactions = get_list_for_transactions(
			doctype, txt, filters + customer_filters, limit_start, limit_page_length, fields='name',
			ignore_permissions=True, order_by='modified desc')
	if suppliers:
		# Get transactions linked by Supplier
		supplier_transactions = get_list_for_transactions(
			doctype, txt, filters + supplier_filters, limit_start, limit_page_length,
			fields='name', ignore_permissions=True, order_by='modified desc')
	if customers and suppliers:
		# Combine customer and supplier documents
		customer_doc_names = {d.name for d in transactions}
		# Filter to remove duplicates
		for transaction in supplier_transactions:
			if transaction.name not in customer_doc_names:
				transactions.append(transaction)
		# Sort by modified
		transactions.sort(key=operator.attrgetter('modified'))
	elif suppliers:
		# No customers
		transactions = supplier_transactions

	return post_process(doctype, transactions)

def get_list_for_transactions(doctype, txt, filters, limit_start, limit_page_length=20,
	ignore_permissions=False, fields=None, order_by=None):
	""" Get List of transactions like Invoices, Orders """
	from frappe.www.list import get_list
	meta = frappe.get_meta(doctype)
	data = []
	or_filters = []

	for d in get_list(doctype, txt, filters=filters, fields=["name", "modified"], limit_start=limit_start,
		limit_page_length=limit_page_length, ignore_permissions=ignore_permissions, order_by=order_by):
		data.append(d)

	# TODO - remove the rest of this code if it doesn't actually do anything?
	# What is it supposed to do?
	if txt:
		if meta.get_field('items'):
			if meta.get_field('items').options:
				child_doctype = meta.get_field('items').options
				for item in frappe.get_all(child_doctype, {"item_name": ['like', "%" + txt + "%"]}):
					child = frappe.get_doc(child_doctype, item.name)
					or_filters.append([doctype, "name", "=", child.parent])

	if or_filters:
		for r in frappe.get_list(doctype, fields=fields + ['modified'], filters=filters,
				or_filters=or_filters, limit_start=limit_start,
				limit_page_length=limit_page_length, ignore_permissions=ignore_permissions,
				order_by=order_by):
			data.append(r)

	return data

def rfq_transaction_list(parties, limit_start, limit_page_length):
	# TODO - check all of this
	data = frappe.db.sql(
		"""select distinct parent as name, supplier from `tabRequest for Quotation Supplier`
		where supplier = %(supplier)s and docstatus=1
		order by modified desc limit %(start)s, %(len)s""",
		{'supplier': parties[0], 'start': frappe.cint(limit_start),
			'len': frappe.cint(limit_page_length)},
		as_dict=1)

	return post_process('Request for Quotation', data)

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
	"""Returns a list of customers and suppliers linked, by user->contact,
	to documents of DocType 'doctype', for User 'user'.
	"""
	roles = frappe.get_roles(user)
	customers = []
	suppliers = []
	meta = frappe.get_meta(doctype)

	has_customer_field = meta.has_field(get_customer_field_name(doctype))
	has_supplier_field = meta.has_field(get_supplier_field_name(doctype))

	customers = suppliers = None
	# If the user has either the roles 'Supplier' or 'Customer', we search
	# for contacts linked to them and linked to our target doctype
	if has_common(["Supplier", "Customer"], roles):
		contacts = frappe.db.sql("""
			select
				`tabDynamic Link`.link_doctype,
				`tabDynamic Link`.link_name
			from
				`tabContact`, `tabDynamic Link`
			where
				`tabContact`.name=`tabDynamic Link`.parent and `tabContact`.user = %s
			""", user, as_dict=1)
		# Return the list of customers and suppliers if the doctype
		# has that field and the user has the relevant Role.
		if has_customer_field and ("Customer" in roles):
			customers = [c.link_name for c in contacts if c.link_doctype == 'Customer']
		if has_supplier_field and ("Supplier" in roles):
			suppliers = [c.link_name for c in contacts if c.link_doctype == 'Supplier']

	return customers, suppliers

def has_website_permission(doc, ptype, user, verbose=False):
	"""Checks if the user 'user' has website permission for document 'doc'
	based on role-based permissions or contact linking
	permissions (for website users with either the Customer or Supplier
	role).
	WARNING - the 'ptype' argument is not used.
	Returns either True, if permission given, or False, if permission denied.
	"""
	doctype = doc.doctype
	# Guest user never has permission
	if user == 'Guest':
		return False
	# Check for standard permissions
	if frappe.has_permission(doctype, 'read', user=user):
		return True
	# Check for linked contacts
	customers, suppliers = get_customers_suppliers(doctype, user)

	# Check if customers found
	if customers and frappe.db.exists(doctype, get_customer_filter(doc, customers)):
		return True
	# Otherwise, check if suppliers found
	if suppliers and frappe.db.exists(doctype, get_supplier_filter(doc, suppliers)):
		return True
	# Neither customers nor suppliers found
	return False

def get_customer_filter(doc, customers):
	"""Return a filter dict for filtering by customer."""
	doctype = doc.doctype
	filters = frappe._dict()
	filters.name = doc.name
	filters[get_customer_field_name(doctype)] = ['in', customers]
	if doctype == 'Quotation':
		filters.quotation_to = 'Customer'
	return filters

def get_customer_field_name(doctype):
	"""Returns the 'Customer' field name for doctype 'doctype'."""
	if doctype == 'Quotation':
		return 'party_name'
	else:
		return 'customer'

def get_supplier_filter(doc, suppliers):
	"""Return a filter dict for filtering by supplier."""
	doctype = doc.doctype
	filters = frappe._dict()
	filters.name = doc.name
	filters[get_supplier_field_name(doctype)] = ['in', suppliers]

def get_supplier_field_name(doctype):
	"""Returns the 'Supplier' field name for doctype 'doctype'."""
	if doctype == 'Request for Quotation':
		# TODO - check this field
		return 'suppliers'
	else:
		return 'supplier'
