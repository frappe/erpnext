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
import webnotes.defaults

from webnotes.utils import cint
from webnotes import msgprint, _
from webnotes.model.doc import make_autoname

sql = webnotes.conn.sql

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def onload(self):
		self.add_communication_list()

	def autoname(self):
		supp_master_name = webnotes.defaults.get_global_default('supp_master_name')
		
		if supp_master_name == 'Supplier Name':
			if webnotes.conn.exists("Customer", self.doc.supplier_name):
				webnotes.msgprint(_("A Customer exists with same name"), raise_exception=1)
			self.doc.name = self.doc.supplier_name
		else:
			self.doc.name = make_autoname(self.doc.naming_series + '.#####')

	def update_credit_days_limit(self):
		sql("""update tabAccount set credit_days = %s where name = %s""", 
			(cint(self.doc.credit_days), self.doc.name + " - " + self.get_company_abbr()))

	def on_update(self):
		if not self.doc.naming_series:
			self.doc.naming_series = ''

		# create account head
		self.create_account_head()

		# update credit days and limit in account
		self.update_credit_days_limit()

	def check_state(self):
		return "\n" + "\n".join([i[0] for i in sql("select state_name from `tabState` where `tabState`.country='%s' " % self.doc.country)])
	
	def get_payables_group(self):
		g = sql("select payables_group from tabCompany where name=%s", self.doc.company)
		g = g and g[0][0] or ''
		if not g:
			msgprint("Update Company master, assign a default group for Payables")
			raise Exception
		return g

	def add_account(self, ac, par, abbr):
		ac_bean = webnotes.bean({
			"doctype": "Account",
			'account_name':ac,
			'parent_account':par,
			'group_or_ledger':'Group',
			'company':self.doc.company,
			"freeze_account": "No",
		})
		ac_bean.ignore_permissions = True
		ac_bean.insert()
		
		msgprint(_("Created Group ") + ac)
	
	def get_company_abbr(self):
		return sql("select abbr from tabCompany where name=%s", self.doc.company)[0][0]
	
	def get_parent_account(self, abbr):
		if (not self.doc.supplier_type):
			msgprint("Supplier Type is mandatory")
			raise Exception
		
		if not sql("select name from tabAccount where name=%s and debit_or_credit = 'Credit' and ifnull(is_pl_account, 'No') = 'No'", (self.doc.supplier_type + " - " + abbr)):

			# if not group created , create it
			self.add_account(self.doc.supplier_type, self.get_payables_group(), abbr)
		
		return self.doc.supplier_type + " - " + abbr

	def validate(self):
		#validation for Naming Series mandatory field...
		if webnotes.defaults.get_global_default('supp_master_name') == 'Naming Series':
			if not self.doc.naming_series:
				msgprint("Series is Mandatory.", raise_exception=1)
	
	def create_account_head(self):
		if self.doc.company :
			abbr = self.get_company_abbr() 
			parent_account = self.get_parent_account(abbr)
						
			if not sql("select name from tabAccount where name=%s", (self.doc.name + " - " + abbr)):
				ac_bean = webnotes.bean({
					"doctype": "Account",
					'account_name': self.doc.name,
					'parent_account': parent_account,
					'group_or_ledger':'Ledger',
					'company': self.doc.company,
					'account_type': '',
					'tax_rate': '0',
					'master_type': 'Supplier',
					'master_name': self.doc.name,
					"freeze_account": "No"
				})
				ac_bean.ignore_permissions = True
				ac_bean.insert()
				
				msgprint(_("Created Account Head: ") + ac_bean.doc.name)
			else:
				self.check_parent_account(parent_account, abbr)
		else : 
			msgprint("Please select Company under which you want to create account head")
	
	def check_parent_account(self, parent_account, abbr):
		if webnotes.conn.get_value("Account", self.doc.name + " - " + abbr, 
			"parent_account") != parent_account:
			ac = webnotes.bean("Account", self.doc.name + " - " + abbr)
			ac.doc.parent_account = parent_account
			ac.save()
	
	def get_contacts(self,nm):
		if nm:
			contact_details =webnotes.conn.convert_to_lists(sql("select name, CONCAT(IFNULL(first_name,''),' ',IFNULL(last_name,'')),contact_no,email_id from `tabContact` where supplier = '%s'"%nm))
	 
			return contact_details
		else:
			return ''
			
	def delete_supplier_address(self):
		for rec in sql("select * from `tabAddress` where supplier=%s", (self.doc.name,), as_dict=1):
			sql("delete from `tabAddress` where name=%s",(rec['name']))
	
	def delete_supplier_contact(self):
		for rec in sql("select * from `tabContact` where supplier=%s", (self.doc.name,), as_dict=1):
			sql("delete from `tabContact` where name=%s",(rec['name']))
			
	def delete_supplier_communication(self):
		webnotes.conn.sql("""\
			delete from `tabCommunication`
			where supplier = %s and customer is null""", self.doc.name)
			
	def delete_supplier_account(self):
		"""delete supplier's ledger if exist and check balance before deletion"""
		acc = sql("select name from `tabAccount` where master_type = 'Supplier' \
			and master_name = %s and docstatus < 2", self.doc.name)
		if acc:
			from webnotes.model import delete_doc
			delete_doc('Account', acc[0][0])
			
	def on_trash(self):
		self.delete_supplier_address()
		self.delete_supplier_contact()
		self.delete_supplier_communication()
		self.delete_supplier_account()
		
	def on_rename(self, new, old, merge=False):
		#update supplier_name if not naming series
		if webnotes.defaults.get_global_default('supp_master_name') == 'Supplier Name':
			update_fields = [
			('Supplier', 'name'),
			('Address', 'supplier'),
			('Contact', 'supplier'),
			('Purchase Invoice', 'supplier'),
			('Purchase Order', 'supplier'),
			('Purchase Receipt', 'supplier'),
			('Serial No', 'supplier')]
			for rec in update_fields:
				sql("update `tab%s` set supplier_name = %s where `%s` = %s" % \
					(rec[0], '%s', rec[1], '%s'), (new, old))
				
		for account in webnotes.conn.sql("""select name, account_name from 
			tabAccount where master_name=%s and master_type='Supplier'""", old, as_dict=1):
			if account.account_name != new:
				webnotes.rename_doc("Account", account.name, new, merge=merge)

		#update master_name in doctype account
		webnotes.conn.sql("""update `tabAccount` set master_name = %s, 
			master_type = 'Supplier' where master_name = %s""" , (new,old))
