# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cstr, flt, getdate, now_datetime, formatdate
from frappe.model.doc import addchild
from frappe.model.bean import getlist
from frappe import msgprint, _

from frappe.model.controller import DocListController

class WarehouseNotSet(Exception): pass

class DocType(DocListController):
	def onload(self):
		self.doc.fields["__sle_exists"] = self.check_if_sle_exists()
	
	def autoname(self):
		if frappe.conn.get_default("item_naming_by")=="Naming Series":
			from frappe.model.doc import make_autoname
			self.doc.item_code = make_autoname(self.doc.naming_series+'.#####')
		elif not self.doc.item_code:
			msgprint(_("Item Code (item_code) is mandatory because Item naming is not sequential."), raise_exception=1)
			
		self.doc.name = self.doc.item_code
			
	def validate(self):
		if not self.doc.stock_uom:
			msgprint(_("Please enter Default Unit of Measure"), raise_exception=1)
		
		self.check_warehouse_is_set_for_stock_item()
		self.check_stock_uom_with_bin()
		self.add_default_uom_in_conversion_factor_table()
		self.validate_conversion_factor()
		self.validate_item_type()
		self.check_for_active_boms()
		self.fill_customer_code()
		self.check_item_tax()
		self.validate_barcode()
		self.cant_change()
		self.validate_item_type_for_reorder()
		
		if not self.doc.parent_website_sitemap:
			self.doc.parent_website_sitemap = frappe.get_website_sitemap("Item Group", self.doc.item_group)

		if self.doc.name:
			self.old_page_name = frappe.conn.get_value('Item', self.doc.name, 'page_name')
			
	def on_update(self):
		self.validate_name_with_item_group()
		self.update_item_price()

	def check_warehouse_is_set_for_stock_item(self):
		if self.doc.is_stock_item=="Yes" and not self.doc.default_warehouse:
			frappe.msgprint(_("Default Warehouse is mandatory for Stock Item."),
				raise_exception=WarehouseNotSet)
			
	def add_default_uom_in_conversion_factor_table(self):
		uom_conv_list = [d.uom for d in self.doclist.get({"parentfield": "uom_conversion_details"})]
		if self.doc.stock_uom not in uom_conv_list:
			ch = addchild(self.doc, 'uom_conversion_details', 'UOM Conversion Detail', self.doclist)
			ch.uom = self.doc.stock_uom
			ch.conversion_factor = 1
			
		for d in self.doclist.get({"parentfield": "uom_conversion_details"}):
			if d.conversion_factor == 1 and d.uom != self.doc.stock_uom:
				self.doclist.remove(d)
				

	def check_stock_uom_with_bin(self):
		if not self.doc.fields.get("__islocal"):
			matched=True
			ref_uom = frappe.conn.get_value("Stock Ledger Entry", 
				{"item_code": self.doc.name}, "stock_uom")
			if ref_uom:
				if cstr(ref_uom) != cstr(self.doc.stock_uom):
					matched = False
			else:
				bin_list = frappe.conn.sql("select * from tabBin where item_code=%s", 
					self.doc.item_code, as_dict=1)
				for bin in bin_list:
					if (bin.reserved_qty > 0 or bin.ordered_qty > 0 or bin.indented_qty > 0 \
						or bin.planned_qty > 0) and cstr(bin.stock_uom) != cstr(self.doc.stock_uom):
							matched = False
							break
						
				if matched and bin_list:
					frappe.conn.sql("""update tabBin set stock_uom=%s where item_code=%s""",
						(self.doc.stock_uom, self.doc.name))
				
			if not matched:
				frappe.throw(_("Default Unit of Measure can not be changed directly because you have already made some transaction(s) with another UOM. To change default UOM, use 'UOM Replace Utility' tool under Stock module."))
	
	def validate_conversion_factor(self):
		check_list = []
		for d in getlist(self.doclist,'uom_conversion_details'):
			if cstr(d.uom) in check_list:
				msgprint(_("UOM %s has been entered more than once in Conversion Factor Table." %
				 	cstr(d.uom)), raise_exception=1)
			else:
				check_list.append(cstr(d.uom))

			if d.uom and cstr(d.uom) == cstr(self.doc.stock_uom) and flt(d.conversion_factor) != 1:
					msgprint(_("""Conversion Factor of UOM: %s should be equal to 1. As UOM: %s is Stock UOM of Item: %s.""" % 
						(d.uom, d.uom, self.doc.name)), raise_exception=1)
			elif d.uom and cstr(d.uom)!= self.doc.stock_uom and flt(d.conversion_factor) == 1:
				msgprint(_("""Conversion Factor of UOM: %s should not be equal to 1. As UOM: %s is not Stock UOM of Item: %s""" % 
					(d.uom, d.uom, self.doc.name)), raise_exception=1)
					
	def validate_item_type(self):
		if cstr(self.doc.is_manufactured_item) == "No":
			self.doc.is_pro_applicable = "No"

		if self.doc.is_pro_applicable == 'Yes' and self.doc.is_stock_item == 'No':
			frappe.throw(_("As Production Order can be made for this item, \
				it must be a stock item."))

		if self.doc.has_serial_no == 'Yes' and self.doc.is_stock_item == 'No':
			msgprint("'Has Serial No' can not be 'Yes' for non-stock item", raise_exception=1)
			
	def check_for_active_boms(self):
		if self.doc.is_purchase_item != "Yes":
			bom_mat = frappe.conn.sql("""select distinct t1.parent 
				from `tabBOM Item` t1, `tabBOM` t2 where t2.name = t1.parent 
				and t1.item_code =%s and ifnull(t1.bom_no, '') = '' and t2.is_active = 1 
				and t2.docstatus = 1 and t1.docstatus =1 """, self.doc.name)
				
			if bom_mat and bom_mat[0][0]:
				frappe.throw(_("Item must be a purchase item, \
					as it is present in one or many Active BOMs"))
					
		if self.doc.is_manufactured_item != "Yes":
			bom = frappe.conn.sql("""select name from `tabBOM` where item = %s 
				and is_active = 1""", (self.doc.name,))
			if bom and bom[0][0]:
				frappe.throw(_("""Allow Bill of Materials should be 'Yes'. Because one or many \
					active BOMs present for this item"""))
					
	def fill_customer_code(self):
		""" Append all the customer codes and insert into "customer_code" field of item table """
		cust_code=[]
		for d in getlist(self.doclist,'item_customer_details'):
			cust_code.append(d.ref_code)
		self.doc.customer_code=','.join(cust_code)

	def check_item_tax(self):
		"""Check whether Tax Rate is not entered twice for same Tax Type"""
		check_list=[]
		for d in getlist(self.doclist,'item_tax'):
			if d.tax_type:
				account_type = frappe.conn.get_value("Account", d.tax_type, "account_type")
				
				if account_type not in ['Tax', 'Chargeable', 'Income Account', 'Expense Account']:
					msgprint("'%s' is not Tax / Chargeable / Income / Expense Account" % d.tax_type, raise_exception=1)
				else:
					if d.tax_type in check_list:
						msgprint("Rate is entered twice for: '%s'" % d.tax_type, raise_exception=1)
					else:
						check_list.append(d.tax_type)
						
	def validate_barcode(self):
		if self.doc.barcode:
			duplicate = frappe.conn.sql("""select name from tabItem where barcode = %s 
				and name != %s""", (self.doc.barcode, self.doc.name))
			if duplicate:
				msgprint("Barcode: %s already used in item: %s" % 
					(self.doc.barcode, cstr(duplicate[0][0])), raise_exception = 1)

	def cant_change(self):
		if not self.doc.fields.get("__islocal"):
			vals = frappe.conn.get_value("Item", self.doc.name, 
				["has_serial_no", "is_stock_item", "valuation_method"], as_dict=True)
			
			if vals and ((self.doc.is_stock_item == "No" and vals.is_stock_item == "Yes") or 
				vals.has_serial_no != self.doc.has_serial_no or 
				cstr(vals.valuation_method) != cstr(self.doc.valuation_method)):
					if self.check_if_sle_exists() == "exists":
						frappe.throw(_("As there are existing stock transactions for this item, you can not change the values of 'Has Serial No', 'Is Stock Item' and 'Valuation Method'"))
							
	def validate_item_type_for_reorder(self):
		if self.doc.re_order_level or len(self.doclist.get({"parentfield": "item_reorder", 
				"material_request_type": "Purchase"})):
			if not self.doc.is_purchase_item:
				frappe.msgprint(_("""To set reorder level, item must be Purchase Item"""), 
					raise_exception=1)
	
	def check_if_sle_exists(self):
		sle = frappe.conn.sql("""select name from `tabStock Ledger Entry` 
			where item_code = %s""", self.doc.name)
		return sle and 'exists' or 'not exists'

	def validate_name_with_item_group(self):
		# causes problem with tree build
		if frappe.conn.exists("Item Group", self.doc.name):
			frappe.msgprint("An item group exists with same name (%s), \
				please change the item name or rename the item group" % 
				self.doc.name, raise_exception=1)

	def update_item_price(self):
		frappe.conn.sql("""update `tabItem Price` set item_name=%s, 
			item_description=%s, modified=NOW() where item_code=%s""",
			(self.doc.item_name, self.doc.description, self.doc.name))

	def get_page_title(self):
		if self.doc.name==self.doc.item_name:
			page_name_from = self.doc.name
		else:
			page_name_from = self.doc.name + " " + self.doc.item_name
		
		return page_name_from
		
	def get_tax_rate(self, tax_type):
		return { "tax_rate": frappe.conn.get_value("Account", tax_type, "tax_rate") }

	def get_file_details(self, arg = ''):
		file = frappe.conn.sql("select file_group, description from tabFile where name = %s", eval(arg)['file_name'], as_dict = 1)

		ret = {
			'file_group'	:	file and file[0]['file_group'] or '',
			'description'	:	file and file[0]['description'] or ''
		}
		return ret
		
	def on_trash(self):
		frappe.conn.sql("""delete from tabBin where item_code=%s""", self.doc.item_code)

	def before_rename(self, olddn, newdn, merge=False):
		if merge:
			# Validate properties before merging
			if not frappe.conn.exists("Item", newdn):
				frappe.throw(_("Item ") + newdn +_(" does not exists"))
			
			field_list = ["stock_uom", "is_stock_item", "has_serial_no", "has_batch_no"]
			new_properties = [cstr(d) for d in frappe.conn.get_value("Item", newdn, field_list)]
			if new_properties != [cstr(self.doc.fields[fld]) for fld in field_list]:
				frappe.throw(_("To merge, following properties must be same for both items")
					+ ": \n" + ", ".join([self.meta.get_label(fld) for fld in field_list]))

			frappe.conn.sql("delete from `tabBin` where item_code=%s", olddn)

	def after_rename(self, olddn, newdn, merge):
		frappe.conn.set_value("Item", newdn, "item_code", newdn)
			
		if merge:
			self.set_last_purchase_rate(newdn)
			self.recalculate_bin_qty(newdn)
			
	def set_last_purchase_rate(self, newdn):
		last_purchase_rate = get_last_purchase_details(newdn).get("base_rate", 0)
		frappe.conn.set_value("Item", newdn, "last_purchase_rate", last_purchase_rate)
			
	def recalculate_bin_qty(self, newdn):
		from erpnext.utilities.repost_stock import repost_stock
		frappe.conn.auto_commit_on_many_writes = 1
		frappe.conn.set_default("allow_negative_stock", 1)
		
		for warehouse in frappe.conn.sql("select name from `tabWarehouse`"):
			repost_stock(newdn, warehouse[0])
		
		frappe.conn.set_default("allow_negative_stock", 
			frappe.conn.get_value("Stock Settings", None, "allow_negative_stock"))
		frappe.conn.auto_commit_on_many_writes = 0

def validate_end_of_life(item_code, end_of_life=None, verbose=1):
	if not end_of_life:
		end_of_life = frappe.conn.get_value("Item", item_code, "end_of_life")
	
	if end_of_life and getdate(end_of_life) <= now_datetime().date():
		msg = (_("Item") + " %(item_code)s: " + _("reached its end of life on") + \
			" %(date)s. " + _("Please check") + ": %(end_of_life_label)s " + \
			"in Item master") % {
				"item_code": item_code,
				"date": formatdate(end_of_life),
				"end_of_life_label": frappe.get_doctype("Item").get_label("end_of_life")
			}
		
		_msgprint(msg, verbose)
		
def validate_is_stock_item(item_code, is_stock_item=None, verbose=1):
	if not is_stock_item:
		is_stock_item = frappe.conn.get_value("Item", item_code, "is_stock_item")
		
	if is_stock_item != "Yes":
		msg = (_("Item") + " %(item_code)s: " + _("is not a Stock Item")) % {
			"item_code": item_code,
		}
		
		_msgprint(msg, verbose)
		
def validate_cancelled_item(item_code, docstatus=None, verbose=1):
	if docstatus is None:
		docstatus = frappe.conn.get_value("Item", item_code, "docstatus")
	
	if docstatus == 2:
		msg = (_("Item") + " %(item_code)s: " + _("is a cancelled Item")) % {
			"item_code": item_code,
		}
		
		_msgprint(msg, verbose)

def _msgprint(msg, verbose):
	if verbose:
		msgprint(msg, raise_exception=True)
	else:
		raise frappe.ValidationError, msg
		
		
def get_last_purchase_details(item_code, doc_name=None, conversion_rate=1.0):
	"""returns last purchase details in stock uom"""
	# get last purchase order item details
	last_purchase_order = frappe.conn.sql("""\
		select po.name, po.transaction_date, po.conversion_rate,
			po_item.conversion_factor, po_item.base_price_list_rate, 
			po_item.discount_percentage, po_item.base_rate
		from `tabPurchase Order` po, `tabPurchase Order Item` po_item
		where po.docstatus = 1 and po_item.item_code = %s and po.name != %s and 
			po.name = po_item.parent
		order by po.transaction_date desc, po.name desc
		limit 1""", (item_code, cstr(doc_name)), as_dict=1)

	# get last purchase receipt item details		
	last_purchase_receipt = frappe.conn.sql("""\
		select pr.name, pr.posting_date, pr.posting_time, pr.conversion_rate,
			pr_item.conversion_factor, pr_item.base_price_list_rate, pr_item.discount_percentage,
			pr_item.base_rate
		from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pr_item
		where pr.docstatus = 1 and pr_item.item_code = %s and pr.name != %s and
			pr.name = pr_item.parent
		order by pr.posting_date desc, pr.posting_time desc, pr.name desc
		limit 1""", (item_code, cstr(doc_name)), as_dict=1)

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
		return frappe._dict()
	
	conversion_factor = flt(last_purchase.conversion_factor)
	out = frappe._dict({
		"base_price_list_rate": flt(last_purchase.base_price_list_rate) / conversion_factor,
		"base_rate": flt(last_purchase.base_rate) / conversion_factor,
		"discount_percentage": flt(last_purchase.discount_percentage),
		"purchase_date": purchase_date
	})

	conversion_rate = flt(conversion_rate) or 1.0
	out.update({
		"price_list_rate": out.base_price_list_rate / conversion_rate,
		"rate": out.base_rate / conversion_rate,
		"base_rate": out.base_rate
	})
	
	return out