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

from webnotes.utils import cstr, flt
from webnotes.model.doc import addchild
from webnotes.model.wrapper import getlist
from webnotes import msgprint

sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def get_tax_rate(self, tax_type):
		rate = sql("select tax_rate from tabAccount where name = %s", tax_type)
		ret = {
			'tax_rate'	:	rate and flt(rate[0][0]) or 0
		}
		return ret

	def on_update(self):
		self.validate_name_with_item_group()
		
		if self.doc.show_in_website:
			# webpage updates
			self.update_website()
			
		bin = sql("select stock_uom from `tabBin` where item_code = '%s' " % self.doc.item_code)
		if bin and cstr(bin[0][0]) != cstr(self.doc.stock_uom):
			msgprint("Please Update Stock UOM with the help of Stock UOM Replace Utility.")
			raise Exception
		check_list = []
		for d in getlist(self.doclist,'uom_conversion_details'):
			if not self.doc.stock_uom:
				msgprint("Please enter Stock UOM first.")
				raise Exception

			if cstr(d.uom) in check_list:
				msgprint("UOM %s has been entered more than once in Conversion Factor Details." % cstr(d.uom))
				raise Exception
			else:
				check_list.append(cstr(d.uom))

			if cstr(d.uom) == cstr(self.doc.stock_uom):
				if flt(d.conversion_factor) != 1:
					msgprint("Conversion Factor of UOM : %s should be equal to 1. As UOM : %s is Stock UOM of Item: %s." % ( cstr(d.uom), cstr(d.uom), cstr(self.doc.name)))
					raise Exception
			elif cstr(d.uom) != cstr(self.doc.stock_uom) and flt(d.conversion_factor) == 1:
				msgprint("Conversion Factor of UOM : %s should not be equal to 1. As UOM : %s is not Stock UOM of Item: %s." % ( cstr(d.uom), cstr(d.uom), cstr(self.doc.name)))
				raise Exception

		if not cstr(self.doc.stock_uom) in check_list :
			child = addchild( self.doc, 'uom_conversion_details', 
				'UOM Conversion Detail', self.doclist)
			child.uom = self.doc.stock_uom
			child.conversion_factor = 1
			child.save()

	def validate_name_with_item_group(self):
		if webnotes.conn.exists("Item Group", self.doc.name):
			webnotes.msgprint("An item group exists with same name (%s), \
				please change the item name or rename the item group" % 
				self.doc.name, raise_exception=1)

	def update_website(self):
		from website.utils import update_page_name
		if self.doc.name==self.doc.item_name:
			page_name_from = self.doc.name
		else:
			page_name_from = self.doc.name + " " + self.doc.item_name

		update_page_name(self.doc, page_name_from)
		
		from website.helpers.product import invalidate_cache_for
		invalidate_cache_for(self.doc.item_group)

		[invalidate_cache_for(d.item_group) for d in \
			self.doclist.get({"doctype":"Website Item Group"})]

	# On delete 1. Delete BIN (if none of the corrosponding transactions present, it gets deleted. if present, rolled back due to exception)
	def on_trash(self):
		sql("""delete from tabBin where item_code=%s""", self.doc.item_code)
		sql("""delete from `tabStock Ledger Entry` 
			where item_code=%s and is_cancelled='Yes' """, self.doc.item_code)
		
		if self.doc.page_name:
			from website.utils import clear_cache
			clear_cache(self.doc.page_name)
		
	# Check whether Ref Rate is not entered twice for same Price List and Currency
	def check_ref_rate_detail(self):
		check_list=[]
		for d in getlist(self.doclist,'ref_rate_details'):
			if [cstr(d.price_list_name),cstr(d.ref_currency)] in check_list:
				msgprint("Ref Rate is entered twice for Price List : '%s' and Currency : '%s'." % (d.price_list_name,d.ref_currency))
				raise Exception
			else:
				check_list.append([cstr(d.price_list_name),cstr(d.ref_currency)])

	# Append all the customer codes and insert into "customer_code" field of item table
	def fill_customer_code(self):
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

	def check_for_active_boms(self, field_label):
		if field_label in ['Is Active', 'Is Purchase Item']:
			bom_mat = sql("select distinct t1.parent from `tabBOM Item` t1, `tabBOM` t2 where t1.item_code ='%s' and (t1.bom_no = '' or t1.bom_no is NULL) and t2.name = t1.parent and t2.is_active = 1 and t2.docstatus = 1 and t1.docstatus =1 " % self.doc.name )
			if bom_mat and bom_mat[0][0]:
				msgprint("%s should be 'Yes'. As Item %s is present in one or many Active BOMs." % (cstr(field_label), cstr(self.doc.name)))
				raise Exception
		if ((field_label == 'Allow Production Order' 
				and self.doc.is_sub_contracted_item != 'Yes') 
				or (field_label == 'Is Sub Contracted Item' 
				and self.doc.is_manufactured_item != 'Yes')):
			bom = sql("select name from `tabBOM` where item = '%s' and is_active = 1" % cstr(self.doc.name))
			if bom and bom[0][0]:
				msgprint("%s should be 'Yes'. As Item %s is present in one or many Active BOMs." % (cstr(field_label), cstr(self.doc.name)))
				raise Exception
				
	def validate_barcode(self):
		if self.doc.barcode:
			duplicate = sql("select name from tabItem where barcode = %s and name != %s", (self.doc.barcode, self.doc.name))
			if duplicate:
				msgprint("Barcode: %s already used in item: %s" % (self.doc.barcode, cstr(duplicate[0][0])), raise_exception = 1)

	def validate(self):
		fl = {'is_manufactured_item'	:'Allow Bill of Materials',
					'is_sub_contracted_item':'Is Sub Contracted Item',
					'is_purchase_item'			:'Is Purchase Item',
					'is_pro_applicable'		 :'Allow Production Order'}
		for d in fl:
			if cstr(self.doc.fields.get(d)) != 'Yes':
				self.check_for_active_boms(fl[d])
		self.check_ref_rate_detail()
		self.fill_customer_code()
		self.check_item_tax()
		self.validate_barcode()
		self.check_non_asset_warehouse()

		if cstr(self.doc.is_manufactured_item) == "No":
			self.doc.is_pro_applicable = "No"

		if self.doc.is_pro_applicable == 'Yes' and self.doc.is_stock_item == 'No':
			msgprint("As Production Order can be made for this Item, then Is Stock Item Should be 'Yes' as we maintain it's stock. Refer Manufacturing and Inventory section.", raise_exception=1)

		if self.doc.has_serial_no == 'Yes' and self.doc.is_stock_item == 'No':
			msgprint("'Has Serial No' can not be 'Yes' for non-stock item", raise_exception=1)

		if self.doc.name:
			self.old_page_name = webnotes.conn.get_value('Item', self.doc.name, 'page_name')
					
	def check_non_asset_warehouse(self):
		if self.doc.is_asset_item == "Yes":
			existing_qty = sql("select t1.warehouse, t1.actual_qty from tabBin t1, tabWarehouse t2 where t1.item_code=%s and (t2.warehouse_type!='Fixed Asset' or t2.warehouse_type is null) and t1.warehouse=t2.name and t1.actual_qty > 0", self.doc.name)
			for e in existing_qty:
				msgprint("%s Units exist in Warehouse %s, which is not an Asset Warehouse." % (e[1],e[0]))
			if existing_qty:
				msgprint("Please transfer the above quantities to an asset warehouse before changing this item to an asset item.")
				self.doc.is_asset_item = 'No'
				raise Exception

	def get_file_details(self, arg = ''):
		file = sql("select file_group, description from tabFile where name = %s", eval(arg)['file_name'], as_dict = 1)

		ret = {
			'file_group'	:	file and file[0]['file_group'] or '',
			'description'	:	file and file[0]['description'] or ''
		}
		return ret

	def check_if_sle_exists(self):
		sle = sql("select name from `tabStock Ledger Entry` where item_code = %s and ifnull(is_cancelled, 'No') = 'No'", self.doc.name)
		return sle and 'exists' or 'not exists'

	def on_rename(self,newdn,olddn):
		sql("update tabItem set item_code = %s where name = %s", (newdn, olddn))
		if self.doc.page_name:
			from website.utils import clear_cache
			clear_cache(self.doc.page_name)
			
	def prepare_template_args(self):
		from website.helpers.product import get_parent_item_groups, url_for_website
		self.parent_groups = get_parent_item_groups(self.doc.item_group) + [{"name":self.doc.name}]
		self.doc.website_image = url_for_website(self.doc.website_image)

		if self.doc.slideshow:
			from website.helpers.slideshow import get_slideshow
			get_slideshow(self)
			
test_records = [
	[{
		"doctype": "Item",
		"item_code": "_Test Item Home Desktop 100",
		"item_name": "_Test Item Home Desktop 100",
		"description": "_Test Item Home Desktop 100",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "Yes",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"is_sample_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	},
	{
		"doctype": "Item Tax",
		"tax_type": "_Test Account Excise Duty - _TC",
		"tax_rate": 10
	}],
	[{
		"doctype": "Item",
		"item_code": "_Test Item Home Desktop 200",
		"item_name": "_Test Item Home Desktop 200",
		"description": "_Test Item Home Desktop 200",
		"item_group": "_Test Item Group Desktops",
		"is_stock_item": "Yes",
		"is_asset_item": "No",
		"has_batch_no": "No",
		"has_serial_no": "No",
		"is_purchase_item": "Yes",
		"is_sales_item": "Yes",
		"is_service_item": "No",
		"is_sample_item": "No",
		"inspection_required": "No",
		"is_pro_applicable": "No",
		"is_sub_contracted_item": "No",
		"stock_uom": "_Test UOM"
	}],
]