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
				
		self.update_parent_account()
				
	def update_parent_account(self):
		if not self.doc.__islocal and (self.doc.create_account_under != 
			webnotes.conn.get_value("Warehouse", self.doc.name, "create_account_under")):
				warehouse_account = webnotes.conn.get_value("Account", 
					{"account_type": "Warehouse", "company": self.doc.company, 
					"master_name": self.doc.name}, ["name", "parent_account"])
				if warehouse_account and warehouse_account[1] != self.doc.create_account_under:
					acc_bean = webnotes.bean("Account", warehouse_account[0])
					acc_bean.doc.parent_account = self.doc.create_account_under
					acc_bean.save()
				
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
			{"account_type": "Warehouse", "master_name": self.doc.name})
		if warehouse_account:
			webnotes.delete_doc("Account", warehouse_account)
				
		if webnotes.conn.sql("""select name from `tabStock Ledger Entry` 
				where warehouse = %s""", self.doc.name):
			msgprint("""Warehouse can not be deleted as stock ledger entry 
				exists for this warehouse.""", raise_exception=1)
			
	def before_rename(self, olddn, newdn, merge=False):
		# Add company abbr if not provided
		from setup.doctype.company.company import get_name_with_abbr
		new_warehouse = get_name_with_abbr(newdn, self.doc.company)

		if merge:
			if not webnotes.conn.exists("Warehouse", newdn):
				webnotes.throw(_("Warehouse ") + newdn +_(" does not exists"))
				
			if self.doc.company != webnotes.conn.get_value("Warehouse", new_warehouse, "company"):
				webnotes.throw(_("Both Warehouse must belong to same Company"))
				
			webnotes.conn.sql("delete from `tabBin` where warehouse=%s", olddn)
			
		from accounts.utils import rename_account_for
		rename_account_for("Warehouse", olddn, new_warehouse, merge)

		return new_warehouse

	def after_rename(self, olddn, newdn, merge=False):
		if merge:
			self.recalculate_bin_qty(newdn)
			
	def recalculate_bin_qty(self, newdn):
		from utilities.repost_stock import repost_stock
		webnotes.conn.auto_commit_on_many_writes = 1
		webnotes.conn.set_default("allow_negative_stock", 1)
		
		for item in webnotes.conn.sql("""select distinct item_code from (
			select name as item_code from `tabItem` where ifnull(is_stock_item, 'Yes')='Yes'
			union 
			select distinct item_code from tabBin) a"""):
				repost_stock(item[0], newdn)
			
		webnotes.conn.set_default("allow_negative_stock", 
			webnotes.conn.get_value("Stock Settings", None, "allow_negative_stock"))
		webnotes.conn.auto_commit_on_many_writes = 0