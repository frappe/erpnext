# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _
from frappe.modules.utils import get_module_app
from frappe.utils import flt, has_common
from frappe.utils.user import is_website_user


def get_list_context(context=None):
	return {
		"global_number_format": frappe.db.get_default("number_format") or "#,###.##",
		"currency": frappe.db.get_default("currency"),
		"currency_symbols": json.dumps(
			dict(
				frappe.db.sql(
					"""select name, symbol
			from tabCurrency where enabled=1"""
				)
			)
		),
		"row_template": "templates/includes/transaction_row.html",
		"get_list": get_transaction_list,
	}


def get_webform_list_context(module):
	if get_module_app(module) != "erpnext":
		return
	return {"get_list": get_webform_transaction_list}


def get_webform_transaction_list(
	doctype, txt=None, filters=None, limit_start=0, limit_page_length=20, order_by="creation"
):
	"""Get List of transactions for custom doctypes"""
	from frappe.www.list import get_list

	if not filters:
		filters = []

	meta = frappe.get_meta(doctype)

	for d in meta.fields:
		if d.fieldtype == "Link" and d.fieldname != "amended_from":
			allowed_docs = [d.name for d in get_transaction_list(doctype=d.options, custom=True)]
			allowed_docs.append("")
			filters.append((d.fieldname, "in", allowed_docs))

	return get_list(
		doctype,
		txt,
		filters,
		limit_start,
		limit_page_length,
		ignore_permissions=False,
		fields=None,
		order_by="creation",
	)


def get_transaction_list(
	doctype,
	txt=None,
	filters=None,
	limit_start=0,
	limit_page_length=20,
	order_by="creation",
	custom=False,
):
	user = frappe.session.user
	ignore_permissions = False

	if not filters:
		filters = {}

	filters["docstatus"] = ["<", "2"] if doctype in ["Supplier Quotation", "Purchase Invoice"] else 1

	if (user != "Guest" and is_website_user()) or doctype == "Request for Quotation":
		parties_doctype = "Request for Quotation Supplier" if doctype == "Request for Quotation" else doctype
		# find party for this contact
		customers, suppliers = get_customers_suppliers(parties_doctype, user)

		if customers:
			if doctype == "Quotation":
				filters["quotation_to"] = "Customer"
				filters["party_name"] = ["in", customers]
			else:
				filters["customer"] = ["in", customers]
		elif suppliers:
			filters["supplier"] = ["in", suppliers]
		elif not custom:
			return []

		if doctype == "Request for Quotation":
			parties = customers or suppliers
			return rfq_transaction_list(parties_doctype, doctype, parties, limit_start, limit_page_length)

		# Since customers and supplier do not have direct access to internal doctypes
		ignore_permissions = True

		if not customers and not suppliers and custom:
			ignore_permissions = False
			filters = {}

	transactions = get_list_for_transactions(
		doctype,
		txt,
		filters,
		limit_start,
		limit_page_length,
		fields="name",
		ignore_permissions=ignore_permissions,
		order_by="creation desc",
	)

	if custom:
		return transactions

	return post_process(doctype, transactions)


def get_list_for_transactions(
	doctype,
	txt,
	filters,
	limit_start,
	limit_page_length=20,
	ignore_permissions=False,
	fields=None,
	order_by=None,
):
	"""Get List of transactions like Invoices, Orders"""
	from frappe.www.list import get_list

	meta = frappe.get_meta(doctype)
	data = []
	or_filters = []

	for d in get_list(
		doctype,
		txt,
		filters=filters,
		fields="name",
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		ignore_permissions=ignore_permissions,
		order_by="creation desc",
	):
		data.append(d)

	if txt:
		if meta.get_field("items"):
			if meta.get_field("items").options:
				child_doctype = meta.get_field("items").options
				for item in frappe.get_all(child_doctype, {"item_name": ["like", "%" + txt + "%"]}):
					child = frappe.get_doc(child_doctype, item.name)
					or_filters.append([doctype, "name", "=", child.parent])

	if or_filters:
		for r in frappe.get_list(
			doctype,
			fields=fields,
			filters=filters,
			or_filters=or_filters,
			limit_start=limit_start,
			limit_page_length=limit_page_length,
			ignore_permissions=ignore_permissions,
			order_by=order_by,
		):
			data.append(r)

	return data


def rfq_transaction_list(parties_doctype, doctype, parties, limit_start, limit_page_length):
	data = frappe.db.sql(
		"""select distinct parent as name, supplier from `tab{doctype}`
			where supplier = '{supplier}' and docstatus=1  order by creation desc limit {start}, {len}""".format(
			doctype=parties_doctype, supplier=parties[0], start=limit_start, len=limit_page_length
		),
		as_dict=1,
	)

	return post_process(doctype, data)


def post_process(doctype, data):
	result = []
	for d in data:
		doc = frappe.get_doc(doctype, d.name)

		doc.status_percent = 0
		doc.status_display = []

		if doc.get("per_billed"):
			doc.status_percent += flt(doc.per_billed)
			doc.status_display.append(
				_("Billed") if doc.per_billed == 100 else _("{0}% Billed").format(doc.per_billed)
			)

		if doc.get("per_delivered"):
			doc.status_percent += flt(doc.per_delivered, 2)
			doc.status_display.append(
				_("Delivered")
				if flt(doc.per_delivered, 2) == 100
				else _("{0}% Delivered").format(doc.per_delivered)
			)

		if hasattr(doc, "set_indicator"):
			doc.set_indicator()

		doc.status_display = ", ".join(doc.status_display)
		doc.items_preview = ", ".join(d.item_name for d in doc.items if d.item_name)
		result.append(doc)

	return result


def get_customers_suppliers(doctype, user):
	customers = []
	suppliers = []
	meta = frappe.get_meta(doctype)

	customer_field_name = get_customer_field_name(doctype)

	has_customer_field = meta.has_field(customer_field_name)
	has_supplier_field = meta.has_field("supplier")

	if has_common(["Supplier", "Customer"], frappe.get_roles(user)):
		suppliers = get_parents_for_user("Supplier")
		customers = get_parents_for_user("Customer")
	elif frappe.has_permission(doctype, "read", user=user):
		customer_list = frappe.get_list("Customer")
		customers = suppliers = [customer.name for customer in customer_list]

	return customers if has_customer_field else None, suppliers if has_supplier_field else None


def get_parents_for_user(parenttype: str) -> list[str]:
	portal_user = frappe.qb.DocType("Portal User")

	return (
		frappe.qb.from_(portal_user)
		.select(portal_user.parent)
		.where(portal_user.user == frappe.session.user)
		.where(portal_user.parenttype == parenttype)
	).run(pluck="name")


def has_website_permission(doc, ptype, user, verbose=False):
	doctype = doc.doctype
	customers, suppliers = get_customers_suppliers(doctype, user)
	if customers:
		return frappe.db.exists(doctype, get_customer_filter(doc, customers))
	elif suppliers:
		fieldname = "suppliers" if doctype == "Request for Quotation" else "supplier"
		return frappe.db.exists(doctype, {"name": doc.name, fieldname: ["in", suppliers]})
	else:
		return False


def get_customer_filter(doc, customers):
	doctype = doc.doctype
	filters = frappe._dict()
	filters.name = doc.name
	filters[get_customer_field_name(doctype)] = ["in", customers]
	if doctype == "Quotation":
		filters.quotation_to = "Customer"
	return filters


def get_customer_field_name(doctype):
	if doctype == "Quotation":
		return "party_name"
	else:
		return "customer"


def add_role_for_portal_user(portal_user, role):
	"""When a new portal user is added, give appropriate roles to user if
	posssible, else warn user to add roles."""
	if not portal_user.is_new():
		return

	user_doc = frappe.get_doc("User", portal_user.user)
	roles = {r.role for r in user_doc.roles}

	if role in roles:
		return

	if "System Manager" not in frappe.get_roles():
		frappe.msgprint(
			_("Please add {1} role to user {0}.").format(portal_user.user, role),
			alert=True,
		)
		return

	user_doc.add_roles(role)
	frappe.msgprint(_("Added {1} Role to User {0}.").format(frappe.bold(user_doc.name), role), alert=True)
