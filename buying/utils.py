# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
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
			"conversion_rate": 1.0
		}
	"""
	if isinstance(args, basestring):
		args = json.loads(args)
		
	args = webnotes._dict(args)
	
	item_wrapper = webnotes.bean("Item", args.item_code)
	item = item_wrapper.doc
	
	from stock.utils import validate_end_of_life
	validate_end_of_life(item.name, item.end_of_life)
	
	# fetch basic values
	out = webnotes._dict()
	out.update({
		"item_name": item.item_name,
		"item_group": item.item_group,
		"brand": item.brand,
		"description": item.description,
		"qty": 0,
		"stock_uom": item.stock_uom,
		"uom": item.stock_uom,
		"conversion_factor": 1,
		"warehouse": args.warehouse or item.default_warehouse,
		"item_tax_rate": json.dumps(dict(([d.tax_type, d.tax_rate] for d in 
			item_wrapper.doclist.get({"parentfield": "item_tax"})))),
		"batch_no": None,
		"expense_head": item.purchase_account,
		"cost_center": item.cost_center
	})
	
	if args.supplier:
		item_supplier = item_wrapper.doclist.get({"parentfield": "item_supplier_details",
			"supplier": args.supplier})
		if item_supplier:
			out["supplier_part_no"] = item_supplier[0].supplier_part_no
	
	if out.warehouse:
		out.projected_qty = webnotes.conn.get_value("Bin", {"item_code": item.name, 
			"warehouse": out.warehouse}, "projected_qty")
	
	if args.transaction_date and item.lead_time_days:
		out.schedule_date = out.lead_time_date = add_days(args.transaction_date,
			item.lead_time_days)
			
	# set zero
	out.purchase_ref_rate = out.discount_rate = out.purchase_rate = \
		out.import_ref_rate = out.import_rate = 0.0
	
	if args.doctype in ["Purchase Order", "Purchase Invoice", "Purchase Receipt", 
			"Supplier Quotation"]:
		# try fetching from price list
		if args.price_list_name and args.price_list_currency:
			rates_as_per_price_list = get_rates_as_per_price_list(args, item_wrapper.doclist)
			if rates_as_per_price_list:
				out.update(rates_as_per_price_list)
		
		# if not found, fetch from last purchase transaction
		if not out.purchase_rate:
			last_purchase = get_last_purchase_details(item.name, args.docname, args.conversion_rate)
			if last_purchase:
				out.update(last_purchase)
			
	return out

def get_rates_as_per_price_list(args, item_doclist=None):
	if not item_doclist:
		item_doclist = webnotes.bean("Item", args.item_code).doclist
	
	result = item_doclist.get({"parentfield": "ref_rate_details", 
		"price_list_name": args.price_list_name, "ref_currency": args.price_list_currency,
		"buying": 1})
		
	if result:
		purchase_ref_rate = flt(result[0].ref_rate) * flt(args.plc_conversion_rate)
		conversion_rate = flt(args.conversion_rate) or 1.0
		return webnotes._dict({
			"purchase_ref_rate": purchase_ref_rate,
			"purchase_rate": purchase_ref_rate,
			"rate": purchase_ref_rate,
			"discount_rate": 0,
			"import_ref_rate": purchase_ref_rate / conversion_rate,
			"import_rate": purchase_ref_rate / conversion_rate
		})
	else:
		return webnotes._dict()

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