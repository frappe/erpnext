# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, get_datetime, format_datetime

class StockOverReturnError(frappe.ValidationError): pass


def validate_return(doc):
	if not doc.meta.get_field("is_return") or not doc.is_return:
		return
		
	validate_return_against(doc)
	validate_returned_items(doc)
			
def validate_return_against(doc):
	if not doc.return_against:
		frappe.throw(_("{0} is mandatory for Return").format(doc.meta.get_label("return_against")))
	else:
		filters = {"doctype": doc.doctype, "docstatus": 1, "company": doc.company}
		if doc.meta.get_field("customer"):
			filters["customer"] = doc.customer
		elif doc.meta.get_field("supplier"):
			filters["supplier"] = doc.supplier
			
		if not frappe.db.exists(filters):
				frappe.throw(_("Invalid {0}: {1}")
					.format(doc.meta.get_label("return_against"), doc.return_against))
		else:
			ref_doc = frappe.get_doc(doc.doctype, doc.return_against)
				
			# validate posting date time
			return_posting_datetime = "%s %s" % (doc.posting_date, doc.get("posting_time") or "00:00:00")
			ref_posting_datetime = "%s %s" % (ref_doc.posting_date, ref_doc.get("posting_time") or "00:00:00")
			
			if get_datetime(return_posting_datetime) < get_datetime(ref_posting_datetime):
				frappe.throw(_("Posting timestamp must be after {0}").format(format_datetime(ref_posting_datetime)))
			
			# validate same exchange rate
			if doc.conversion_rate != ref_doc.conversion_rate:
				frappe.throw(_("Exchange Rate must be same as {0} {1} ({2})")
					.format(doc.doctype, doc.return_against, ref_doc.conversion_rate))
					
			# validate update stock
			if doc.doctype == "Sales Invoice" and doc.update_stock and not ref_doc.update_stock:
					frappe.throw(_("'Update Stock' can not be checked because items are not delivered via {0}")
						.format(doc.return_against))
				
def validate_returned_items(doc):
	valid_items = frappe._dict()
	for d in frappe.db.sql("""select item_code, sum(qty) as qty, rate from `tab{0} Item` 
		where parent = %s group by item_code""".format(doc.doctype), doc.return_against, as_dict=1):
			valid_items.setdefault(d.item_code, d)
	
	if doc.doctype in ("Delivery Note", "Sales Invoice"):
		for d in frappe.db.sql("""select item_code, sum(qty) as qty from `tabPacked Item` 
			where parent = %s group by item_code""".format(doc.doctype), doc.return_against, as_dict=1):
				valid_items.setdefault(d.item_code, d)
			
	already_returned_items = get_already_returned_items(doc)
	
	items_returned = False
	for d in doc.get("items"):
		if flt(d.qty) < 0:
			if d.item_code not in valid_items:
				frappe.throw(_("Row # {0}: Returned Item {1} does not exists in {2} {3}")
					.format(d.idx, d.item_code, doc.doctype, doc.return_against))
			else:
				ref = valid_items.get(d.item_code, frappe._dict())
				already_returned_qty = flt(already_returned_items.get(d.item_code))
				max_return_qty = flt(ref.qty) - already_returned_qty
				
				if already_returned_qty >= ref.qty:
					frappe.throw(_("Item {0} has already been returned").format(d.item_code), StockOverReturnError)
				elif abs(d.qty) > max_return_qty:
					frappe.throw(_("Row # {0}: Cannot return more than {1} for Item {2}")
						.format(d.idx, ref.qty, d.item_code), StockOverReturnError)
				elif ref.rate and flt(d.rate) != ref.rate:
					frappe.throw(_("Row # {0}: Rate must be same as {1} {2}")
						.format(d.idx, doc.doctype, doc.return_against))
				
			
			items_returned = True
			
	if not items_returned:
		frappe.throw(_("Atleast one item should be entered with negative quantity in return document"))
		
def get_already_returned_items(doc):
	return frappe._dict(frappe.db.sql("""
		select 
			child.item_code, sum(abs(child.qty)) as qty
		from 
			`tab{0} Item` child, `tab{1}` par 
		where 
			child.parent = par.name and par.docstatus = 1
			and ifnull(par.is_return, 0) = 1 and par.return_against = %s and child.qty < 0 
		group by item_code
	""".format(doc.doctype, doc.doctype), doc.return_against))
	
def make_return_doc(doctype, source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	def set_missing_values(source, target):
		doc = frappe.get_doc(target)
		doc.is_return = 1
		doc.return_against = source.name
		doc.ignore_pricing_rule = 1
		doc.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = -1* source_doc.qty
		if doctype == "Purchase Receipt":
			target_doc.received_qty = -1* source_doc.qty
		elif doctype == "Purchase Invoice":
			target_doc.purchase_receipt = source_doc.purchase_receipt
			target_doc.pr_detail = source_doc.pr_detail

	doclist = get_mapped_doc(doctype, source_name,	{
		doctype: {
			"doctype": doctype,
			
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		doctype +" Item": {
			"doctype": doctype + " Item",
			"fields": {
				"purchase_order": "purchase_order",
				"purchase_receipt": "purchase_receipt"
			},
			"postprocess": update_item
		},
	}, target_doc, set_missing_values)

	return doclist
