# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import flt, validate_email_add
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def autoname(self):
		suffix = " - " + webnotes.conn.get_value("Company", self.doc.company, "abbr")
		if not self.doc.warehouse_name.endswith(suffix):
			self.doc.name = self.doc.warehouse_name + suffix
	
	def get_bin(self, item_code, warehouse=None):
		warehouse = warehouse or self.doc.name
		bin = sql("select name from tabBin where item_code = %s and \
				warehouse = %s", (item_code, warehouse))
		bin = bin and bin[0][0] or ''
		if not bin:
			bin_wrapper = webnotes.bean([{
				"doctype": "Bin",
				"item_code": item_code,
				"warehouse": warehouse,
			}])
			bin_wrapper.ignore_permissions = 1
			bin_wrapper.insert()
			
			bin_obj = bin_wrapper.make_controller()
		else:
			bin_obj = get_obj('Bin', bin)
		return bin_obj
	
	def update_bin(self, args):
		is_stock_item = webnotes.conn.get_value('Item', args.get("item_code"), 'is_stock_item')
		if is_stock_item == 'Yes':
			bin = self.get_bin(args.get("item_code"))
			bin.update_stock(args)
			return bin
		else:
			msgprint("[Stock Update] Ignored %s since it is not a stock item" 
				% args.get("item_code"))

	def validate(self):
		if self.doc.email_id and not validate_email_add(self.doc.email_id):
				msgprint("Please enter valid Email Id", raise_exception=1)

	def merge_warehouses(self):
		webnotes.conn.auto_commit_on_many_writes = 1
		
		# get items which dealt with current warehouse
		items = webnotes.conn.sql("select item_code from tabBin where warehouse=%s"	, self.doc.name)
		# delete old bins
		webnotes.conn.sql("delete from tabBin where warehouse=%s", self.doc.name)
		
		# replace link fields
		from webnotes.model import rename_doc
		link_fields = rename_doc.get_link_fields('Warehouse')
		rename_doc.update_link_field_values(link_fields, self.doc.name, self.doc.merge_with)
		
		for item_code in items:
			self.repost(item_code[0], self.doc.merge_with)
			
		webnotes.conn.auto_commit_on_many_writes = 0
		
		msgprint("Warehouse %s merged into %s. Now you can delete warehouse: %s" 
			% (self.doc.name, self.doc.merge_with, self.doc.name))
		

	def repost(self, item_code, warehouse=None):
		self.repost_actual_qty(item_code, warehouse)
		
		bin = self.get_bin(item_code, warehouse)
		self.repost_reserved_qty(bin)
		self.repost_indented_qty(bin)
		self.repost_ordered_qty(bin)
		self.repost_planned_qty(bin)
		bin.doc.projected_qty = flt(bin.doc.actual_qty) + flt(bin.doc.planned_qty) \
			+ flt(bin.doc.indented_qty) + flt(bin.doc.ordered_qty) - flt(bin.doc.reserved_qty)
		bin.doc.save()
			

	def repost_actual_qty(self, item_code, warehouse=None):
		from stock.stock_ledger import update_entries_after
		if not warehouse:
			warehouse = self.doc.name
		
		update_entries_after({ "item_code": item_code, "warehouse": warehouse })

	def repost_reserved_qty(self, bin):
		reserved_qty = webnotes.conn.sql("""
			select 
				sum((dnpi_qty / so_item_qty) * (so_item_qty - so_item_delivered_qty))
			from 
				(
					select
						qty as dnpi_qty,
						(
							select qty from `tabSales Order Item`
							where name = dnpi.parent_detail_docname
						) as so_item_qty,
						(
							select ifnull(delivered_qty, 0) from `tabSales Order Item`
							where name = dnpi.parent_detail_docname
						) as so_item_delivered_qty
					from 
					(
						select qty, parent_detail_docname
						from `tabDelivery Note Packing Item` dnpi_in
						where item_code = %s and warehouse = %s
						and parenttype="Sales Order"
						and exists (select * from `tabSales Order` so
						where name = dnpi_in.parent and docstatus = 1 and status != 'Stopped')
					) dnpi
				) tab 
			where 
				so_item_qty >= so_item_delivered_qty
		""", (bin.doc.item_code, bin.doc.warehouse))

		if flt(bin.doc.reserved_qty) != flt(reserved_qty[0][0]):
			webnotes.conn.set_value("Bin", bin.doc.name, "reserved_qty", flt(reserved_qty[0][0]))


	def repost_indented_qty(self, bin):
		indented_qty = webnotes.conn.sql("""select sum(pr_item.qty - pr_item.ordered_qty)
			from `tabMaterial Request Item` pr_item, `tabMaterial Request` pr
			where pr_item.item_code=%s and pr_item.warehouse=%s 
			and pr_item.qty > pr_item.ordered_qty and pr_item.parent=pr.name 
			and pr.status!='Stopped' and pr.docstatus=1"""
			, (bin.doc.item_code, bin.doc.warehouse))
			
		if flt(bin.doc.indented_qty) != flt(indented_qty[0][0]):
			webnotes.conn.set_value("Bin", bin.doc.name, "indented_qty", flt(indented_qty[0][0]))
		
	
	def repost_ordered_qty(self, bin):
		ordered_qty = webnotes.conn.sql("""
			select sum((po_item.qty - po_item.received_qty)*po_item.conversion_factor)
			from `tabPurchase Order Item` po_item, `tabPurchase Order` po
			where po_item.item_code=%s and po_item.warehouse=%s 
			and po_item.qty > po_item.received_qty and po_item.parent=po.name 
			and po.status!='Stopped' and po.docstatus=1"""
			, (bin.doc.item_code, bin.doc.warehouse))
			
		if flt(bin.doc.ordered_qty) != flt(ordered_qty[0][0]):
			webnotes.conn.set_value("Bin", bin.doc.name, "ordered_qty", flt(ordered_qty[0][0]))

	def repost_planned_qty(self, bin):
		planned_qty = webnotes.conn.sql("""
			select sum(qty - produced_qty) from `tabProduction Order` 
			where production_item = %s and fg_warehouse = %s and status != "Stopped"
			and docstatus=1""", (bin.doc.item_code, bin.doc.warehouse))

		if flt(bin.doc.planned_qty) != flt(planned_qty[0][0]):
			webnotes.conn.set_value("Bin", bin.doc.name, "planned_qty", flt(planned_qty[0][0]))

	def on_trash(self):
		# delete bin
		bins = sql("select * from `tabBin` where warehouse = %s", self.doc.name, as_dict=1)
		for d in bins:
			if d['actual_qty'] or d['reserved_qty'] or d['ordered_qty'] or \
					d['indented_qty'] or d['projected_qty'] or d['planned_qty']:
				msgprint("""Warehouse: %s can not be deleted as qty exists for item: %s""" 
					% (self.doc.name, d['item_code']), raise_exception=1)
			else:
				sql("delete from `tabBin` where name = %s", d['name'])
				
		# delete cancelled sle
		if sql("""select name from `tabStock Ledger Entry` 
				where warehouse = %s and ifnull('is_cancelled', '') = 'No'""", self.doc.name):
			msgprint("""Warehosue can not be deleted as stock ledger entry 
				exists for this warehouse.""", raise_exception=1)
		else:
			sql("delete from `tabStock Ledger Entry` where warehouse = %s", self.doc.name)

	def on_rename(self, newdn, olddn, merge=False):
		if merge:
			from stock.stock_ledger import update_entries_after
			for item_code in webnotes.conn.sql("""select item_code from `tabBin` 
				where warehouse=%s""", newdn):
					update_entries_after({"item_code": item_code, "warehouse": newdn})
