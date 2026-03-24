# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import formatdate
from pypika import Order

from erpnext.controllers.website_list_for_contact import get_customers_suppliers


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)
	context.parents = frappe.form_dict.parents
	context.doc.supplier = get_supplier()
	context.doc.rfq_links = get_link_quotation(context.doc.supplier, context.doc.name)
	unauthorized_user(context.doc.supplier)
	update_supplier_details(context)
	context["title"] = frappe.form_dict.name


def get_supplier():
	doctype = frappe.form_dict.doctype
	parties_doctype = "Request for Quotation Supplier" if doctype == "Request for Quotation" else doctype
	customers, suppliers = get_customers_suppliers(parties_doctype, frappe.session.user)

	return suppliers[0] if suppliers else ""


def check_supplier_has_docname_access(supplier):
	return frappe.form_dict.name in frappe.get_all(
		"Request for Quotation Supplier", filters={"supplier": supplier}, pluck="parent"
	)


def unauthorized_user(supplier):
	status = check_supplier_has_docname_access(supplier) or False
	if status is False:
		frappe.throw(_("Not Permitted"), frappe.PermissionError)


def update_supplier_details(context):
	supplier_doc = frappe.get_doc("Supplier", context.doc.supplier)
	context.doc.currency = supplier_doc.default_currency or frappe.get_cached_value(
		"Company", context.doc.company, "default_currency"
	)
	context.doc.currency_symbol = frappe.db.get_value("Currency", context.doc.currency, "symbol", cache=True)
	context.doc.number_format = frappe.db.get_value(
		"Currency", context.doc.currency, "number_format", cache=True
	)
	context.doc.buying_price_list = supplier_doc.default_price_list or ""


def get_link_quotation(supplier, rfq):
	supplier_quotation = frappe.qb.DocType("Supplier Quotation")
	supplier_quotation_item = frappe.qb.DocType("Supplier Quotation Item")
	quotation = (
		frappe.qb.from_(supplier_quotation_item)
		.join(supplier_quotation)
		.on(supplier_quotation_item.parent == supplier_quotation.name)
		.select(
			supplier_quotation_item.parent.as_("name"),
			supplier_quotation.status,
			supplier_quotation.transaction_date,
		)
		.where(
			(supplier_quotation.docstatus < 2)
			& (supplier_quotation_item.request_for_quotation == rfq)
			& (supplier_quotation.supplier == supplier)
		)
		.distinct()
		.orderby(supplier_quotation.creation, order=Order.desc)
	).run(as_dict=True)

	for data in quotation:
		data.transaction_date = formatdate(data.transaction_date)

	return quotation or None
