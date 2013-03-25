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

from webnotes.utils import flt, fmt_money
from webnotes import msgprint

sql = webnotes.conn.sql
get_value = webnotes.conn.get_value

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl
		self.nsm_parent_field = 'parent_account'

	def autoname(self):
		self.doc.name = self.doc.account_name.strip() + ' - ' + \
			webnotes.conn.get_value("Company", self.doc.company, "abbr")

	def get_address(self):
		address = webnotes.conn.get_value(self.doc.master_type, self.doc.master_name, "address")
		return {'address': address}
		
	def validate_master_name(self):
		if (self.doc.master_type == 'Customer' or self.doc.master_type == 'Supplier') \
				and not self.doc.master_name:
			msgprint("Message: Please enter Master Name once the account is created.")
			
	def validate_parent(self):
		"""Fetch Parent Details and validation for account not to be created under ledger"""
		if self.doc.parent_account:
			par = sql("""select name, group_or_ledger, is_pl_account, debit_or_credit 
				from tabAccount where name =%s""", self.doc.parent_account)
			if not par:
				msgprint("Parent account does not exists", raise_exception=1)
			elif par[0][0] == self.doc.name:
				msgprint("You can not assign itself as parent account", raise_exception=1)
			elif par[0][1] != 'Group':
				msgprint("Parent account can not be a ledger", raise_exception=1)
			elif self.doc.debit_or_credit and par[0][3] != self.doc.debit_or_credit:
				msgprint("You can not move a %s account under %s account" % 
					(self.doc.debit_or_credit, par[0][3]), raise_exception=1)
			
			if not self.doc.is_pl_account:
				self.doc.is_pl_account = par[0][2]
			if not self.doc.debit_or_credit:
				self.doc.debit_or_credit = par[0][3]

	def validate_max_root_accounts(self):
		if webnotes.conn.sql("""select count(*) from tabAccount where
			company=%s and ifnull(parent_account,'')='' and docstatus != 2""",
			self.doc.company)[0][0] > 4:
			webnotes.msgprint("One company cannot have more than 4 root Accounts",
				raise_exception=1)
	
	def validate_duplicate_account(self):
		if (self.doc.fields.get('__islocal') or not self.doc.name) and \
				sql("""select name from tabAccount where account_name=%s and company=%s""", 
					(self.doc.account_name, self.doc.company)):
			msgprint("Account Name: %s already exists, please rename" 
				% self.doc.account_name, raise_exception=1)
				
	def validate_root_details(self):
		#does not exists parent
		if webnotes.conn.exists("Account", self.doc.name):
			if not webnotes.conn.get_value("Account", self.doc.name, "parent_account"):
				webnotes.msgprint("Root cannot be edited.", raise_exception=1)
			
	def convert_group_to_ledger(self):
		if self.check_if_child_exists():
			msgprint("Account: %s has existing child. You can not convert this account to ledger" % 
				(self.doc.name), raise_exception=1)
		elif self.check_gle_exists():
			msgprint("Account with existing transaction can not be converted to ledger.", 
				raise_exception=1)
		else:
			self.doc.group_or_ledger = 'Ledger'
			self.doc.save()
			return 1

	def convert_ledger_to_group(self):
		if self.check_gle_exists():
			msgprint("Account with existing transaction can not be converted to group.", 
				raise_exception=1)
		elif self.doc.master_type or self.doc.account_type:
			msgprint("Cannot covert to Group because Master Type or Account Type is selected.", 
				raise_exception=1)
		else:
			self.doc.group_or_ledger = 'Group'
			self.doc.save()
			return 1

	# Check if any previous balance exists
	def check_gle_exists(self):
		exists = sql("""select name from `tabGL Entry` where account = %s
			and ifnull(is_cancelled, 'No') = 'No'""", self.doc.name)
		return exists and exists[0][0] or ''

	def check_if_child_exists(self):
		return sql("""select name from `tabAccount` where parent_account = %s 
			and docstatus != 2""", self.doc.name)
	
	def validate_mandatory(self):
		if not self.doc.debit_or_credit:
			msgprint("Debit or Credit field is mandatory", raise_exception=1)
		if not self.doc.is_pl_account:
			msgprint("Is PL Account field is mandatory", raise_exception=1)

	def validate(self): 
		self.validate_master_name()
		self.validate_parent()
		self.validate_duplicate_account()
		self.validate_root_details()
		self.validate_mandatory()
	
		if not self.doc.parent_account:
			self.doc.parent_account = ''

	def update_nsm_model(self):
		import webnotes
		import webnotes.utils.nestedset
		webnotes.utils.nestedset.update_nsm(self)
			
	def on_update(self):
		self.validate_max_root_accounts()
		self.update_nsm_model()		

	def get_authorized_user(self):
		# Check logged-in user is authorized
		if webnotes.conn.get_value('Global Defaults', None, 'credit_controller') \
				in webnotes.user.get_roles():
			return 1
			
	def check_credit_limit(self, account, company, tot_outstanding):
		# Get credit limit
		credit_limit_from = 'Customer'

		cr_limit = sql("""select t1.credit_limit from tabCustomer t1, `tabAccount` t2 
			where t2.name=%s and t1.name = t2.master_name""", account)
		credit_limit = cr_limit and flt(cr_limit[0][0]) or 0
		if not credit_limit:
			credit_limit = webnotes.conn.get_value('Company', company, 'credit_limit')
			credit_limit_from = 'global settings in the Company'
		
		# If outstanding greater than credit limit and not authorized person raise exception
		if credit_limit > 0 and flt(tot_outstanding) > credit_limit \
				and not self.get_authorized_user():
			msgprint("""Total Outstanding amount (%s) for <b>%s</b> can not be \
				greater than credit limit (%s). To change your credit limit settings, \
				please update the <b>%s</b>""" % (fmt_money(tot_outstanding), 
				account, fmt_money(credit_limit), credit_limit_from), raise_exception=1)
			
	def validate_trash(self):
		"""checks gl entries and if child exists"""
		if not self.doc.parent_account:
			msgprint("Root account can not be deleted", raise_exception=1)
			
		if self.check_gle_exists():
			msgprint("""Account with existing transaction (Sales Invoice / Purchase Invoice / \
				Journal Voucher) can not be trashed""", raise_exception=1)
		if self.check_if_child_exists():
			msgprint("Child account exists for this account. You can not trash this account.",
			 	raise_exception=1)

	def on_trash(self): 
		self.validate_trash()
		self.update_nsm_model()

		# delete all cancelled gl entry of this account
		sql("""delete from `tabGL Entry` where account = %s and 
			ifnull(is_cancelled, 'No') = 'Yes'""", self.doc.name)

	def on_rename(self, new, old):
		company_abbr = webnotes.conn.get_value("Company", self.doc.company, "abbr")		
		parts = new.split(" - ")	

		if parts[-1].lower() != company_abbr.lower():
			parts.append(company_abbr)

		# rename account name
		account_name = " - ".join(parts[:-1])
		sql("update `tabAccount` set account_name = %s where name = %s", (account_name, old))

		return " - ".join(parts)

def get_master_name(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select name from `tab%s` where %s like %s 
		order by name limit %s, %s""" %
		(filters["master_type"], searchfield, "%s", "%s", "%s"), 
		("%%%s%%" % txt, start, page_len), as_list=1)
		
def get_parent_account(doctype, txt, searchfield, start, page_len, filters):
	return webnotes.conn.sql("""select name from tabAccount 
		where group_or_ledger = 'Group' and docstatus != 2 and company = %s
		and %s like %s order by name limit %s, %s""" % 
		("%s", searchfield, "%s", "%s", "%s"), 
		(filters["company"], "%%%s%%" % txt, start, page_len), as_list=1)