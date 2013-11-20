# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, validate_email_add
from webnotes import msgprint, _

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def autoname(self):
		suffix = " - " + webnotes.conn.get_value("Company", self.doc.company, "abbr")
		if not self.doc.warehouse_name.endswith(suffix):
			self.doc.name = self.doc.warehouse_name + suffix

	def validate(self):
		if self.doc.email_id and not validate_email_add(self.doc.email_id):
				msgprint("Please enter valid Email Id", raise_exception=1)
				
	def on_update(self):
		self.create_account_head()
						
	def create_account_head(self):
		if cint(webnotes.defaults.get_global_default("auto_accounting_for_stock")):
			if not webnotes.conn.get_value("Account", {"account_type": "Warehouse", 
					"master_name": self.doc.name}) and not webnotes.conn.get_value("Account", 
					{"account_name": self.doc.warehouse_name}):
				if self.doc.fields.get("__islocal") or not webnotes.conn.get_value(
						"Stock Ledger Entry", {"warehouse": self.doc.name}):
					self.validate_parent_account()
					ac_bean = webnotes.bean({
						"doctype": "Account",
						'account_name': self.doc.warehouse_name, 
						'parent_account': self.doc.create_account_under, 
						'group_or_ledger':'Ledger', 
						'company':self.doc.company, 
						"account_type": "Warehouse",
						"master_name": self.doc.name,
						"freeze_account": "No"
					})
					ac_bean.ignore_permissions = True
					ac_bean.insert()
					
					msgprint(_("Account Head") + ": " + ac_bean.doc.name + _(" created"))
	
	def validate_parent_account(self):
		if not self.doc.create_account_under:
			parent_account = webnotes.conn.get_value("Account", 
				{"account_name": "Stock Assets", "company": self.doc.company})
			if parent_account:
				self.doc.create_account_under = parent_account
			else:
				webnotes.throw(_("Please enter account group under which account \
					for warehouse ") + self.doc.name +_(" will be created"))
			
	def on_rename(self, new, old, merge=False):
		webnotes.conn.set_value("Account", {"account_type": "Warehouse", "master_name": old}, 
			"master_name", new)
			
		if merge:
			from stock.stock_ledger import update_entries_after
			for item_code in webnotes.conn.sql("""select item_code from `tabBin` 
				where warehouse=%s""", new):
					update_entries_after({"item_code": item_code, "warehouse": new})

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
		
		account_link_fields = rename_doc.get_link_fields('Account')
		old_warehouse_account = webnotes.conn.get_value("Account", {"master_name": self.doc.name})
		new_warehouse_account = webnotes.conn.get_value("Account", 
			{"master_name": self.doc.merge_with})
		rename_doc.update_link_field_values(account_link_fields, old_warehouse_account, 
			new_warehouse_account)
			
		webnotes.conn.delete_doc("Account", old_warehouse_account)
		
		from utilities.repost_stock import repost
		for item_code in items:
			repost(item_code[0], self.doc.merge_with)
			
		webnotes.conn.auto_commit_on_many_writes = 0
		
		msgprint("Warehouse %s merged into %s. Now you can delete warehouse: %s" 
			% (self.doc.name, self.doc.merge_with, self.doc.name))
		
	def on_trash(self):
		# delete bin
		bins = webnotes.conn.sql("select * from `tabBin` where warehouse = %s", 
			self.doc.name, as_dict=1)
		for d in bins:
			if d['actual_qty'] or d['reserved_qty'] or d['ordered_qty'] or \
					d['indented_qty'] or d['projected_qty'] or d['planned_qty']:
				msgprint("""Warehouse: %s can not be deleted as qty exists for item: %s""" 
					% (self.doc.name, d['item_code']), raise_exception=1)
			else:
				webnotes.conn.sql("delete from `tabBin` where name = %s", d['name'])
				
		warehouse_account = webnotes.conn.get_value("Account", 
			{"account_type": "Warehosue", "master_name": self.doc.name})
		if warehouse_account:
			webnotes.delete_doc("Account", warehouse_account)
				
		# delete cancelled sle
		if webnotes.conn.sql("""select name from `tabStock Ledger Entry` where warehouse = %s""", 
				self.doc.name):
			msgprint("""Warehosue can not be deleted as stock ledger entry 
				exists for this warehouse.""", raise_exception=1)
		else:
			webnotes.conn.sql("delete from `tabStock Ledger Entry` where warehouse = %s", 
				self.doc.name)
