# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import getdate, flt, add_days
import json

@webnotes.whitelist()
def get_item_details(args):
	"""
		args = {
			"doctype": "",
			"docname": "",
			"item_code": "",
			"warehouse": None,
			"supplier": None,
			"transaction_date": None,
			"conversion_rate": 1.0,
			"buying_price_list": None,
			"price_list_currency": None,
			"plc_conversion_rate": 1.0,
			"is_subcontracted": "Yes" / "No"
		}
	"""
	if isinstance(args, basestring):
		args = json.loads(args)
		
	args = webnotes._dict(args)
	
	item_bean = webnotes.bean("Item", args.item_code)
	item = item_bean.doc
	
	_validate_item_details(args, item)
	
	out = _get_basic_details(args, item_bean)
	
	out.supplier_part_no = _get_supplier_part_no(args, item_bean)
	
	if not out.warehouse:
		out.warehouse = item_bean.doc.default_warehouse
	
	if out.warehouse:
		out.projected_qty = get_projected_qty(item.name, out.warehouse)
	
	if args.transaction_date and item.lead_time_days:
		out.schedule_date = out.lead_time_date = add_days(args.transaction_date,
			item.lead_time_days)
			
	meta = webnotes.get_doctype(args.doctype)
	
	if meta.get_field("currency"):
		out.purchase_ref_rate = out.discount_rate = out.purchase_rate = \
			out.import_ref_rate = out.import_rate = 0.0
		out.update(_get_price_list_rate(args, item_bean, meta))
	
	if args.doctype == "Material Request":
		out.min_order_qty = flt(item.min_order_qty)
	
	return out
	
def _get_basic_details(args, item_bean):
	item = item_bean.doc
	
	out = webnotes._dict({
		"description": item.description_html or item.description,
		"qty": 1.0,
		"uom": item.stock_uom,
		"conversion_factor": 1.0,
		"warehouse": args.warehouse or item.default_warehouse,
		"item_tax_rate": json.dumps(dict(([d.tax_type, d.tax_rate] for d in 
			item_bean.doclist.get({"parentfield": "item_tax"})))),
		"batch_no": None,
		"expense_head": item.purchase_account \
			or webnotes.conn.get_value("Company", args.company, "default_expense_account"),
		"cost_center": item.cost_center
	})
	
	for fieldname in ("item_name", "item_group", "brand", "stock_uom"):
		out[fieldname] = item.fields.get(fieldname)
	
	return out
	
def _get_price_list_rate(args, item_bean, meta):
	from utilities.transaction_base import validate_currency
	item = item_bean.doc
	out = webnotes._dict()
	
	# try fetching from price list
	if args.buying_price_list and args.price_list_currency:
		price_list_rate = webnotes.conn.sql("""select ref_rate from `tabItem Price` 
			where price_list=%s and item_code=%s and buying_or_selling='Buying'""", 
			(args.buying_price_list, args.item_code), as_dict=1)
		
		if price_list_rate:
			from utilities.transaction_base import validate_currency
			validate_currency(args, item_bean.doc, meta)
				
			out.import_ref_rate = flt(price_list_rate[0].ref_rate) * \
				flt(args.plc_conversion_rate) / flt(args.conversion_rate)
		
	# if not found, fetch from last purchase transaction
	if not out.import_ref_rate:
		last_purchase = get_last_purchase_details(item.name, args.docname, args.conversion_rate)
		if last_purchase:
			out.update(last_purchase)
	
	if out.import_ref_rate or out.import_rate:
		validate_currency(args, item, meta)
	
	return out
	
def _get_supplier_part_no(args, item_bean):
	item_supplier = item_bean.doclist.get({"parentfield": "item_supplier_details",
		"supplier": args.supplier})
	
	return item_supplier and item_supplier[0].supplier_part_no or None

def _validate_item_details(args, item):
	from utilities.transaction_base import validate_item_fetch
	validate_item_fetch(args, item)
	
	# validate if purchase item or subcontracted item
	if item.is_purchase_item != "Yes":
		msgprint(_("Item") + (" %s: " % item.name) + _("not a purchase item"),
			raise_exception=True)
	
	if args.is_subcontracted == "Yes" and item.is_sub_contracted_item != "Yes":
		msgprint(_("Item") + (" %s: " % item.name) + 
			_("not a sub-contracted item.") +
			_("Please select a sub-contracted item or do not sub-contract the transaction."), 
			raise_exception=True)

def get_last_purchase_details(item_code, doc_name, conversion_rate=1.0):
	"""returns last purchase details in stock uom"""
	# get last purchase order item details
	last_purchase_order = webnotes.conn.sql("""\
		select po.name, po.transaction_date, po.conversion_rate,
			po_item.conversion_factor, po_item.purchase_ref_rate, 
			po_item.discount_rate, po_item.purchase_rate
		from `tabPurchase Order` po, `tabPurchase Order Item` po_item
		where po.docstatus = 1 and po_item.item_code = %s and po.name != %s and 
			po.name = po_item.parent
		order by po.transaction_date desc, po.name desc
		limit 1""", (item_code, doc_name), as_dict=1)

	# get last purchase receipt item details		
	last_purchase_receipt = webnotes.conn.sql("""\
		select pr.name, pr.posting_date, pr.posting_time, pr.conversion_rate,
			pr_item.conversion_factor, pr_item.purchase_ref_rate, pr_item.discount_rate,
			pr_item.purchase_rate
		from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
		where pr.docstatus = 1 and pr_item.item_code = %s and pr.name != %s and
			pr.name = pr_item.parent
		order by pr.posting_date desc, pr.posting_time desc, pr.name desc
		limit 1""", (item_code, doc_name), as_dict=1)

	purchase_order_date = getdate(last_purchase_order and last_purchase_order[0].transaction_date \
		or "1900-01-01")
	purchase_receipt_date = getdate(last_purchase_receipt and \
		last_purchase_receipt[0].posting_date or "1900-01-01")

	if (purchase_order_date > purchase_receipt_date) or \
			(last_purchase_order and not last_purchase_receipt):
		# use purchase order
		last_purchase = last_purchase_order[0]
		purchase_date = purchase_order_date
		
	elif (purchase_receipt_date > purchase_order_date) or \
			(last_purchase_receipt and not last_purchase_order):
		# use purchase receipt
		last_purchase = last_purchase_receipt[0]
		purchase_date = purchase_receipt_date
		
	else:
		return webnotes._dict()
	
	conversion_factor = flt(last_purchase.conversion_factor)
	out = webnotes._dict({
		"purchase_ref_rate": flt(last_purchase.purchase_ref_rate) / conversion_factor,
		"purchase_rate": flt(last_purchase.purchase_rate) / conversion_factor,
		"discount_rate": flt(last_purchase.discount_rate),
		"purchase_date": purchase_date
	})

	conversion_rate = flt(conversion_rate) or 1.0
	out.update({
		"import_ref_rate": out.purchase_ref_rate / conversion_rate,
		"import_rate": out.purchase_rate / conversion_rate,
		"rate": out.purchase_rate
	})
	
	return out
	
@webnotes.whitelist()
def get_conversion_factor(item_code, uom):
	return {"conversion_factor": webnotes.conn.get_value("UOM Conversion Detail",
		{"parent": item_code, "uom": uom}, "conversion_factor")}
		
@webnotes.whitelist()
def get_projected_qty(item_code, warehouse):
	return webnotes.conn.get_value("Bin", {"item_code": item_code, 
			"warehouse": warehouse}, "projected_qty")