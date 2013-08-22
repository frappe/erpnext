# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt, cint
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes import msgprint, _

from webnotes.model.controller import DocListController

class PriceListCurrencyMismatch(Exception): pass
class WarehouseNotSet(Exception): pass

class DocType(DocListController):
	def autoname(self):
		if webnotes.conn.get_default("item_naming_by")=="Naming Series":
			from webnotes.model.doc import make_autoname
			self.doc.item_code = make_autoname(self.doc.naming_series+'.#####')
		elif not self.doc.item_code:
			msgprint(_("Item Code (item_code) is mandatory because Item naming is not sequential."), raise_exception=1)
			
		self.doc.name = self.doc.item_code
			
	def validate(self):
		if not self.doc.stock_uom:
			msgprint(_("Please enter Default Unit of Measure"), raise_exception=1)
		
		self.check_warehouse_is_set_for_stock_item()
		self.check_stock_uom_with_bin()
		self.validate_conversion_factor()
		self.add_default_uom_in_conversion_factor_table()
		self.valiadte_item_type()
		self.check_for_active_boms()
		self.validate_price_lists()
		self.fill_customer_code()
		self.check_item_tax()
		self.validate_barcode()
		self.cant_change()
		self.validate_item_type_for_reorder()

		if self.doc.name:
			self.old_page_name = webnotes.conn.get_value('Item', self.doc.name, 'page_name')
			
	def on_update(self):
		self.validate_name_with_item_group()
		self.update_website()

	def check_warehouse_is_set_for_stock_item(self):
		if self.doc.is_stock_item=="Yes" and not self.doc.default_warehouse:
			webnotes.msgprint(_("Default Warehouse is mandatory for Stock Item."),
				raise_exception=WarehouseNotSet)
			
	def add_default_uom_in_conversion_factor_table(self):
		uom_conv_list = [d.uom for d in self.doclist.get({"parentfield": "uom_conversion_details"})]
		if self.doc.stock_uom not in uom_conv_list:
			ch = addchild(self.doc, 'uom_conversion_details', 'UOM Conversion Detail', self.doclist)
			ch.uom = self.doc.stock_uom
			ch.conversion_factor = 1

	def check_stock_uom_with_bin(self):
		if not self.doc.fields.get("__islocal"):
			bin = webnotes.conn.sql("select stock_uom from `tabBin` where item_code = %s", 
				self.doc.name)
			if self.doc.stock_uom and bin and cstr(bin[0][0]) \
					and cstr(bin[0][0]) != cstr(self.doc.stock_uom):
				msgprint(_("Please Update Stock UOM with the help of Stock UOM Replace Utility."), 
					raise_exception=1)
	
	def validate_conversion_factor(self):
		check_list = []
		for d in getlist(self.doclist,'uom_conversion_details'):
			if cstr(d.uom) in check_list:
				msgprint(_("UOM %s has been entered more than once in Conversion Factor Table." %
				 	cstr(d.uom)), raise_exception=1)
			else:
				check_list.append(cstr(d.uom))

			if d.uom and cstr(d.uom) == cstr(self.doc.stock_uom) and flt(d.conversion_factor) != 1:
					msgprint(_("""Conversion Factor of UOM: %s should be equal to 1. 
						As UOM: %s is Stock UOM of Item: %s.""" % 
						(d.uom, d.uom, self.doc.name)), raise_exception=1)
			elif d.uom and cstr(d.uom)!= self.doc.stock_uom and flt(d.conversion_factor) == 1:
				msgprint(_("""Conversion Factor of UOM: %s should not be equal to 1. 
					As UOM: %s is not Stock UOM of Item: %s""" % 
					(d.uom, d.uom, self.doc.name)), raise_exception=1)
					
	def valiadte_item_type(self):
		if cstr(self.doc.is_manufactured_item) == "No":
			self.doc.is_pro_applicable = "No"

		if self.doc.is_pro_applicable == 'Yes' and self.doc.is_stock_item == 'No':
			msgprint("As Production Order can be made for this Item, then Is Stock Item Should be 'Yes' as we maintain it's stock. Refer Manufacturing and Inventory section.", raise_exception=1)

		if self.doc.has_serial_no == 'Yes' and self.doc.is_stock_item == 'No':
			msgprint("'Has Serial No' can not be 'Yes' for non-stock item", raise_exception=1)
			
	def check_for_active_boms(self):
		def _check_for_active_boms(field_label):
			if field_label in ['Is Active', 'Is Purchase Item']:
				bom_mat = webnotes.conn.sql("""select distinct t1.parent 
					from `tabBOM Item` t1, `tabBOM` t2 where t2.name = t1.parent 
					and t1.item_code =%s and ifnull(t1.bom_no, '') = '' and t2.is_active = 1 
					and t2.docstatus = 1 and t1.docstatus =1 """, self.doc.name)
				if bom_mat and bom_mat[0][0]:
					msgprint(_(field_label) + _(" should be 'Yes'. As Item: ") + self.doc.name + 
						_(" is present in one or many Active BOMs"), raise_exception=1)
						
			if ((field_label == 'Allow Production Order' 
					and self.doc.is_sub_contracted_item != 'Yes') 
					or (field_label == 'Is Sub Contracted Item' 
					and self.doc.is_manufactured_item != 'Yes')):
				bom = webnotes.conn.sql("""select name from `tabBOM` where item = %s 
					and is_active = 1""", (self.doc.name,))
				if bom and bom[0][0]:
					msgprint(_(field_label) + _(" should be 'Yes'. As Item: ") + self.doc.name + 
						_(" is present in one or many Active BOMs"), raise_exception=1)
		
		if not cint(self.doc.fields.get("__islocal")):
			fl = {'is_manufactured_item'	:'Allow Bill of Materials',
					'is_sub_contracted_item':'Is Sub Contracted Item',
					'is_purchase_item'			:'Is Purchase Item',
					'is_pro_applicable'		 :'Allow Production Order'}
			for d in fl:
				if cstr(self.doc.fields.get(d)) != 'Yes':
					_check_for_active_boms(fl[d])
			
	def validate_price_lists(self):
		price_lists=[]
		for d in getlist(self.doclist,'ref_rate_details'):
			if d.price_list in price_lists:
				msgprint(_("Cannot have two prices for same Price List") + ": " + d.price_list,
					raise_exception= webnotes.DuplicateEntryError)
			else:
				price_list_currency = webnotes.conn.get_value("Price List", d.price_list, "currency")
				if price_list_currency and d.ref_currency != price_list_currency:
					msgprint(_("Currency does not match Price List Currency for Price List") \
						+ ": " + d.price_list, raise_exception=PriceListCurrencyMismatch)
				
				price_lists.append(d.price_list)
			
					
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
				account_type = webnotes.conn.get_value("Account", d.tax_type, "account_type")
				
				if account_type not in ['Tax', 'Chargeable']:
					msgprint("'%s' is not Tax / Chargeable Account" % d.tax_type, raise_exception=1)
				else:
					if d.tax_type in check_list:
						msgprint("Rate is entered twice for: '%s'" % d.tax_type, raise_exception=1)
					else:
						check_list.append(d.tax_type)
						
	def validate_barcode(self):
		if self.doc.barcode:
			duplicate = webnotes.conn.sql("""select name from tabItem where barcode = %s 
				and name != %s""", (self.doc.barcode, self.doc.name))
			if duplicate:
				msgprint("Barcode: %s already used in item: %s" % 
					(self.doc.barcode, cstr(duplicate[0][0])), raise_exception = 1)

	def cant_change(self):
		if not self.doc.fields.get("__islocal"):
			vals = webnotes.conn.get_value("Item", self.doc.name, 
				["has_serial_no", "is_stock_item", "valuation_method"], as_dict=True)
			
			if vals and ((self.doc.is_stock_item == "No" and vals.is_stock_item == "Yes") or 
				vals.has_serial_no != self.doc.has_serial_no or 
				cstr(vals.valuation_method) != cstr(self.doc.valuation_method)):
					if self.check_if_sle_exists() == "exists":
						webnotes.msgprint(_("As there are existing stock transactions for this \
							item, you can not change the values of 'Has Serial No', \
							'Is Stock Item' and 'Valuation Method'"), raise_exception=1)
							
	def validate_item_type_for_reorder(self):
		if self.doc.re_order_level or len(self.doclist.get({"parentfield": "item_reorder", 
				"material_request_type": "Purchase"})):
			if not self.doc.is_purchase_item:
				webnotes.msgprint(_("""To set reorder level, item must be Purchase Item"""), 
					raise_exception=1)
	
	def check_if_sle_exists(self):
		sle = webnotes.conn.sql("""select name from `tabStock Ledger Entry` 
			where item_code = %s and ifnull(is_cancelled, 'No') = 'No'""", self.doc.name)
		return sle and 'exists' or 'not exists'

	def validate_name_with_item_group(self):
		if webnotes.conn.exists("Item Group", self.doc.name):
			webnotes.msgprint("An item group exists with same name (%s), \
				please change the item name or rename the item group" % 
				self.doc.name, raise_exception=1)

	def update_website(self):
		def _invalidate_cache():
			from website.helpers.product import invalidate_cache_for
			
			invalidate_cache_for(self.doc.item_group)

			[invalidate_cache_for(d.item_group) for d in \
				self.doclist.get({"doctype":"Website Item Group"})]
		
		if self.doc.show_in_website:
			from webnotes.webutils import update_page_name
			if self.doc.name==self.doc.item_name:
				page_name_from = self.doc.name
			else:
				page_name_from = self.doc.name + " " + self.doc.item_name

			update_page_name(self.doc, page_name_from)
			
			_invalidate_cache()
		
		elif self.doc.page_name:
			# if unchecked show in website
			from webnotes.webutils import delete_page_cache
			delete_page_cache(self.doc.page_name)
			
			_invalidate_cache()
			
			webnotes.conn.set(self.doc, "page_name", None)

	def get_tax_rate(self, tax_type):
		return { "tax_rate": webnotes.conn.get_value("Account", tax_type, "tax_rate") }

	def prepare_template_args(self):
		from website.helpers.product import get_parent_item_groups
		self.parent_groups = get_parent_item_groups(self.doc.item_group) + [{"name":self.doc.name}]
		self.doc.title = self.doc.item_name

		if self.doc.slideshow:
			from website.helpers.slideshow import get_slideshow
			get_slideshow(self)								

	def get_file_details(self, arg = ''):
		file = webnotes.conn.sql("select file_group, description from tabFile where name = %s", eval(arg)['file_name'], as_dict = 1)

		ret = {
			'file_group'	:	file and file[0]['file_group'] or '',
			'description'	:	file and file[0]['description'] or ''
		}
		return ret
		
	def on_trash(self):
		webnotes.conn.sql("""delete from tabBin where item_code=%s""", self.doc.item_code)
		webnotes.conn.sql("""delete from `tabStock Ledger Entry` 
			where item_code=%s and is_cancelled='Yes' """, self.doc.item_code)

		if self.doc.page_name:
			from webnotes.webutils import clear_cache
			clear_cache(self.doc.page_name)

	def on_rename(self, newdn, olddn, merge=False):
		webnotes.conn.sql("update tabItem set item_code = %s where name = %s", (newdn, olddn))
		if self.doc.page_name:
			from webnotes.webutils import clear_cache
			clear_cache(self.doc.page_name)
			
		if merge:
			from stock.stock_ledger import update_entries_after
			for wh in webnotes.conn.sql("""select warehouse from `tabBin` 
				where item_code=%s""", newdn):
					update_entries_after({"item_code": newdn, "warehouse": wh[0]})
