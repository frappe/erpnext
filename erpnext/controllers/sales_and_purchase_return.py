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
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

	valid_items = frappe._dict()

	select_fields = "item_code, qty, rate, parenttype" if doc.doctype=="Purchase Invoice" \
		else "item_code, qty, rate, serial_no, batch_no, parenttype"

	if doc.doctype in ['Purchase Invoice', 'Purchase Receipt']:
		select_fields += ",rejected_qty, received_qty"

	for d in frappe.db.sql("""select {0} from `tab{1} Item` where parent = %s"""
		.format(select_fields, doc.doctype), doc.return_against, as_dict=1):
			valid_items = get_ref_item_dict(valid_items, d)

	if doc.doctype in ("Delivery Note", "Sales Invoice"):
		for d in frappe.db.sql("""select item_code, qty, serial_no, batch_no from `tabPacked Item`
			where parent = %s""".format(doc.doctype), doc.return_against, as_dict=1):
				valid_items = get_ref_item_dict(valid_items, d)

	already_returned_items = get_already_returned_items(doc)

	# ( not mandatory when it is Purchase Invoice or a Sales Invoice without Update Stock )
	warehouse_mandatory = not (doc.doctype=="Purchase Invoice" or (doc.doctype=="Sales Invoice" and not doc.update_stock))

	items_returned = False
	for d in doc.get("items"):
		if flt(d.qty) < 0 or d.get('received_qty') < 0:
			if d.item_code not in valid_items:
				frappe.throw(_("Row # {0}: Returned Item {1} does not exists in {2} {3}")
					.format(d.idx, d.item_code, doc.doctype, doc.return_against))
			else:
				ref = valid_items.get(d.item_code, frappe._dict())
				validate_quantity(doc, d, ref, valid_items, already_returned_items)
				
				if ref.rate and doc.doctype in ("Delivery Note", "Sales Invoice") and flt(d.rate) > ref.rate:
					frappe.throw(_("Row # {0}: Rate cannot be greater than the rate used in {1} {2}")
						.format(d.idx, doc.doctype, doc.return_against))
							
				elif ref.batch_no and d.batch_no not in ref.batch_no:
					frappe.throw(_("Row # {0}: Batch No must be same as {1} {2}")
						.format(d.idx, doc.doctype, doc.return_against))
						
				elif ref.serial_no:
					if not d.serial_no:
						frappe.throw(_("Row # {0}: Serial No is mandatory").format(d.idx))
					else:
						serial_nos = get_serial_nos(d.serial_no)
						for s in serial_nos:
							if s not in ref.serial_no:
								frappe.throw(_("Row # {0}: Serial No {1} does not match with {2} {3}")
									.format(d.idx, s, doc.doctype, doc.return_against))

				if warehouse_mandatory and not d.get("warehouse"):
					frappe.throw(_("Warehouse is mandatory"))

			items_returned = True

	if not items_returned:
		frappe.throw(_("Atleast one item should be entered with negative quantity in return document"))

def validate_quantity(doc, args, ref, valid_items, already_returned_items):
	fields = ['qty']
	if doc.doctype in ['Purchase Receipt', 'Purchase Invoice']:
		fields.extend(['received_qty', 'rejected_qty'])

	already_returned_data = already_returned_items.get(args.item_code) or {}

	for column in fields:
		returned_qty = flt(already_returned_data.get(column, 0)) if len(already_returned_data) > 0 else 0
		reference_qty = ref.get(column)
		max_returnable_qty = flt(reference_qty) - returned_qty
		label = column.replace('_', ' ').title()
		if reference_qty:	
			if flt(args.get(column)) > 0:
				frappe.throw(_("{0} must be negative in return document").format(label))
			elif returned_qty >= reference_qty and args.get(column):
				frappe.throw(_("Item {0} has already been returned")
					.format(args.item_code), StockOverReturnError)
			elif abs(args.get(column)) > max_returnable_qty:
				frappe.throw(_("Row # {0}: Cannot return more than {1} for Item {2}")
					.format(args.idx, reference_qty, args.item_code), StockOverReturnError)

def get_ref_item_dict(valid_items, ref_item_row):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
	
	valid_items.setdefault(ref_item_row.item_code, frappe._dict({
		"qty": 0,
		"rate": 0,
		"rejected_qty": 0,
		"received_qty": 0,
		"serial_no": [],
		"batch_no": []
	}))
	item_dict = valid_items[ref_item_row.item_code]
	item_dict["qty"] += ref_item_row.qty
	item_dict["rate"] = ref_item_row.get("rate", 0)

	if ref_item_row.parenttype in ['Purchase Invoice', 'Purchase Receipt']:
		item_dict["received_qty"] += ref_item_row.received_qty
		item_dict["rejected_qty"] += ref_item_row.rejected_qty

	if ref_item_row.get("serial_no"):
		item_dict["serial_no"] += get_serial_nos(ref_item_row.serial_no)
		
	if ref_item_row.get("batch_no"):
		item_dict["batch_no"].append(ref_item_row.batch_no)
		
	return valid_items

def get_already_returned_items(doc):
	column = 'child.item_code, sum(abs(child.qty)) as qty'
	if doc.doctype in ['Purchase Invoice', 'Purchase Receipt']:
		column += ', sum(abs(child.rejected_qty)) as rejected_qty, sum(abs(child.received_qty)) as received_qty'

	data = frappe.db.sql("""
		select {0}
		from
			`tab{1} Item` child, `tab{2}` par
		where
			child.parent = par.name and par.docstatus = 1
			and par.is_return = 1 and par.return_against = %s
		group by item_code
	""".format(column, doc.doctype, doc.doctype), doc.return_against, as_dict=1)

	items = {}

	for d in data:
		items.setdefault(d.item_code, frappe._dict({
			"qty": d.get("qty"),
			"received_qty": d.get("received_qty"),
			"rejected_qty": d.get("rejected_qty")
		}))

	return items

def make_return_doc(doctype, source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	def set_missing_values(source, target):
		doc = frappe.get_doc(target)
		doc.is_return = 1
		doc.return_against = source.name
		doc.ignore_pricing_rule = 1
		if doctype == "Sales Invoice":
			doc.is_pos = source.is_pos

			# look for Print Heading "Credit Note"
			if not doc.select_print_heading:
				doc.select_print_heading = frappe.db.get_value("Print Heading", _("Credit Note"))

		elif doctype == "Purchase Invoice":
			# look for Print Heading "Debit Note"
			doc.select_print_heading = frappe.db.get_value("Print Heading", _("Debit Note"))

		for tax in doc.get("taxes"):
			if tax.charge_type == "Actual":
				tax.tax_amount = -1 * tax.tax_amount

		if doc.get("is_return"):
			if doc.doctype == 'Sales Invoice':
				doc.set('payments', [])
				for data in source.payments:
					doc.append('payments', {
						'mode_of_payment': data.mode_of_payment,
						'type': data.type,
						'amount': -1 * data.amount,
						'base_amount': -1 * data.base_amount
					})
			elif doc.doctype == 'Purchase Invoice':
				doc.paid_amount = -1 * source.paid_amount
				doc.base_paid_amount = -1 * source.base_paid_amount

		doc.discount_amount = -1 * source.discount_amount
		doc.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = -1* source_doc.qty
		if doctype == "Purchase Receipt":
			target_doc.received_qty = -1* source_doc.received_qty
			target_doc.rejected_qty = -1* source_doc.rejected_qty
			target_doc.qty = -1* source_doc.qty
			target_doc.purchase_order = source_doc.purchase_order
			target_doc.purchase_order_item = source_doc.purchase_order_item
			target_doc.rejected_warehouse = source_doc.rejected_warehouse
		elif doctype == "Purchase Invoice":
			target_doc.received_qty = -1* source_doc.received_qty
			target_doc.rejected_qty = -1* source_doc.rejected_qty
			target_doc.qty = -1* source_doc.qty
			target_doc.purchase_order = source_doc.purchase_order
			target_doc.purchase_receipt = source_doc.purchase_receipt
			target_doc.rejected_warehouse = source_doc.rejected_warehouse
			target_doc.po_detail = source_doc.po_detail
			target_doc.pr_detail = source_doc.pr_detail
		elif doctype == "Delivery Note":
			target_doc.against_sales_order = source_doc.against_sales_order
			target_doc.against_sales_invoice = source_doc.against_sales_invoice
			target_doc.so_detail = source_doc.so_detail
			target_doc.si_detail = source_doc.si_detail
			target_doc.expense_account = source_doc.expense_account
		elif doctype == "Sales Invoice":
			target_doc.sales_order = source_doc.sales_order
			target_doc.delivery_note = source_doc.delivery_note
			target_doc.so_detail = source_doc.so_detail
			target_doc.dn_detail = source_doc.dn_detail
			target_doc.expense_account = source_doc.expense_account

	doclist = get_mapped_doc(doctype, source_name,	{
		doctype: {
			"doctype": doctype,

			"validation": {
				"docstatus": ["=", 1],
			}
		},
		doctype +" Item": {
			"doctype": doctype + " Item",
			"field_map": {
				"serial_no": "serial_no",
				"batch_no": "batch_no"
			},
			"postprocess": update_item
		},
	}, target_doc, set_missing_values)

	return doclist
