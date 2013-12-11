# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, flt
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
def get_sales_bom_items(item_code):
	return webnotes.conn.sql("""select t1.item_code, t1.qty, t1.uom 
		from `tabSales BOM Item` t1, `tabSales BOM` t2 
		where t2.new_item_code=%s and t1.parent = t2.name""", item_code, as_dict=1)

def get_packing_item_details(item):
	return webnotes.conn.sql("""select item_name, description, stock_uom from `tabItem` 
		where name = %s""", item, as_dict = 1)[0]

def get_bin_qty(item, warehouse):
	det = webnotes.conn.sql("""select actual_qty, projected_qty from `tabBin` 
		where item_code = %s and warehouse = %s""", (item, warehouse), as_dict = 1)
	return det and det[0] or ''

def update_packing_list_item(obj, packing_item_code, qty, warehouse, line, packing_list_idx):
	bin = get_bin_qty(packing_item_code, warehouse)
	item = get_packing_item_details(packing_item_code)

	# check if exists
	exists = 0
	for d in getlist(obj.doclist, 'packing_details'):
		if d.parent_item == line.item_code and d.item_code == packing_item_code and d.parent_detail_docname == line.name:
			pi, exists = d, 1
			break

	if not exists:
		pi = addchild(obj.doc, 'packing_details', 'Packed Item', obj.doclist)

	pi.parent_item = line.item_code
	pi.item_code = packing_item_code
	pi.item_name = item['item_name']
	pi.parent_detail_docname = line.name
	pi.description = item['description']
	pi.uom = item['stock_uom']
	pi.qty = flt(qty)
	pi.actual_qty = bin and flt(bin['actual_qty']) or 0
	pi.projected_qty = bin and flt(bin['projected_qty']) or 0
	if not pi.warehouse:
		pi.warehouse = warehouse
	if not pi.batch_no:
		pi.batch_no = cstr(line.batch_no)
	pi.idx = packing_list_idx
	
	# saved, since this function is called on_update of delivery note
	pi.save()
	
	packing_list_idx += 1


def make_packing_list(obj, item_table_fieldname):
	"""make packing list for sales bom item"""
	packing_list_idx = 0
	parent_items = []
	for d in obj.doclist.get({"parentfield": item_table_fieldname}):
		warehouse = (item_table_fieldname == "sales_order_details") \
			and d.reserved_warehouse or d.warehouse
		if webnotes.conn.get_value("Sales BOM", {"new_item_code": d.item_code}):
			for i in get_sales_bom_items(d.item_code):
				update_packing_list_item(obj, i['item_code'], flt(i['qty'])*flt(d.qty), 
					warehouse, d, packing_list_idx)

			if [d.item_code, d.name] not in parent_items:
				parent_items.append([d.item_code, d.name])
			
	obj.doclist = cleanup_packing_list(obj, parent_items)
	
	return obj.doclist
	
def cleanup_packing_list(obj, parent_items):
	"""Remove all those child items which are no longer present in main item table"""
	delete_list = []
	for d in obj.doclist.get({"parentfield": "packing_details"}):
		if [d.parent_item, d.parent_detail_docname] not in parent_items:
			# mark for deletion from doclist
			delete_list.append(d.name)

	if not delete_list:
		return obj.doclist
	
	# delete from doclist
	obj.doclist = webnotes.doclist(filter(lambda d: d.name not in delete_list, obj.doclist))
	
	# delete from db
	webnotes.conn.sql("""\
		delete from `tabPacked Item`
		where name in (%s)"""
		% (", ".join(["%s"] * len(delete_list))),
		tuple(delete_list))
		
	return obj.doclist