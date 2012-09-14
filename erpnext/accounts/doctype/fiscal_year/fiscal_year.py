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

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d,dl
		
	def repost(self):
		if not self.doc.company:
			msgprint("Please select company", raise_exception=1)
			
		if not in_transaction:
			sql("start transaction")
		
		self.rebuid_account_tree()		
		self.clear_account_balances()
		self.create_account_balances()
		self.update_opening(self.doc.company)
		self.post_entries()
		sql("commit")
		
		msgprint("Account balance reposted for fiscal year: " + self.doc.name)
		
	def rebuid_account_tree(self):
		from webnotes.utils.nestedset import rebuild_tree
		rebuild_tree('Account', 'parent_account')
		
	def clear_account_balances(self):
		# balances clear - `tabAccount Balance` for fiscal year
		sql("update `tabAccount Balance` t1, tabAccount t2 set t1.opening=0, t1.balance=0, t1.debit=0, t1.credit=0 where t1.fiscal_year=%s and t2.company = %s and t1.account = t2.name", (self.doc.name, self.doc.company))

	def create_account_balances(self):
		# get periods
		period_list = self.get_period_list()
		cnt = 0
		
		# get accounts
		al = sql("select name from tabAccount")
		
		for a in al:
			# check
			if sql("select count(*) from `tabAccount Balance` where fiscal_year=%s and account=%s", (self.doc.name, a[0]))[0][0] < 13:
				for p in period_list:
					# check if missing
					if not sql("select name from `tabAccount Balance` where period=%s and account=%s and fiscal_year=%s", (p[0], a[0], self.doc.name)):
						d = Document('Account Balance')
						d.account = a[0]
						d.period = p[0]
						d.start_date = p[1].strftime('%Y-%m-%d')
						d.end_date = p[2].strftime('%Y-%m-%d')
						d.fiscal_year = p[3]
						d.debit = 0
						d.credit = 0
						d.opening = 0
						d.balance = 0
						d.save(1)
						cnt += 1
				if cnt % 100 == 0:
					sql("commit")
					sql("start transaction")
		return cnt
				
	# Get periods(month and year)
	#=================================
	def get_period_list(self):
		periods = []
		pl = sql("SELECT name, start_date, end_date, fiscal_year FROM tabPeriod WHERE fiscal_year = '%s' and period_type in ('Month', 'Year') order by start_date ASC, end_date DESC" % self.doc.name)
		for p in pl:
			periods.append([p[0], p[1], p[2], p[3]])
		return periods

	# ====================================================================================
	def update_opening(self, company):
		"""
			set opening from last year closing
		
		"""
		
		abl = sql("select t1.account, t1.balance from `tabAccount Balance` t1, tabAccount t2 where t1.period= '%s' and t2.company= '%s' and ifnull(t2.is_pl_account, 'No') = 'No' and t1.account = t2.name for update" % (self.doc.past_year, company))
		
		cnt = 0
		for ab in abl:
			if cnt % 100 == 0:
				sql("commit")
				sql("start transaction")
		
			sql("update `tabAccount Balance` set opening=%s where period=%s and account=%s", (ab[1], self.doc.name, ab[0]))
			sql("update `tabAccount Balance` set balance=%s where fiscal_year=%s and account=%s", (ab[1], self.doc.name, ab[0]))
			cnt += 1
		
		return cnt
			
	def get_account_details(self, account):
		return sql("select debit_or_credit, lft, rgt, is_pl_account from tabAccount where name=%s", account)[0]

	# ====================================================================================
	def post_entries(self):
		sql("LOCK TABLE `tabGL Entry` WRITE")
		# post each gl entry (batch or complete)
		gle = sql("select name, account, debit, credit, is_opening, posting_date from `tabGL Entry` where fiscal_year=%s and ifnull(is_cancelled,'No')='No' and company=%s", (self.doc.name, self.doc.company))
		account_details = {}

		cnt = 0
		for entry in gle:
			# commit in batches of 100
			if cnt % 100 == 0: 
				sql("commit")
				sql("start transaction")
			cnt += 1
			#print cnt

			if not account_details.has_key(entry[1]):
				account_details[entry[1]] = self.get_account_details(entry[1])
			
			det = account_details[entry[1]]
			diff = flt(entry[2])-flt(entry[3])
			if det[0]=='Credit': diff = -diff

			# build dict
			p = {
				'debit': entry[4]=='No' and flt(entry[2]) or 0
				,'credit': entry[4]=='No' and flt(entry[3]) or 0
				,'opening': entry[4]=='Yes' and diff or 0
				
				# end date conditino only if it is not opening
				,'end_date_condition':(entry[4]!='Yes' and ("and ab.end_date >= '"+entry[5].strftime('%Y-%m-%d')+"'") or '')
				,'diff': diff
				,'lft': det[1]
				,'rgt': det[2]
				,'posting_date': entry[5]
				,'fiscal_year': self.doc.name
			}
		
			sql("""update `tabAccount Balance` ab, `tabAccount` a 
					set 
						ab.debit = ifnull(ab.debit,0) + %(debit)s
						,ab.credit = ifnull(ab.credit,0) + %(credit)s
						,ab.opening = ifnull(ab.opening,0) + %(opening)s
						,ab.balance = ifnull(ab.balance,0) + %(diff)s
					where
						a.lft <= %(lft)s
						and a.rgt >= %(rgt)s
						and ab.account = a.name
						%(end_date_condition)s
						and ab.fiscal_year = '%(fiscal_year)s' """ % p)

		sql("UNLOCK TABLES")


	# Clear PV/RV outstanding
	# ====================================================================================
	def clear_outstanding(self):
		# clear o/s of current year
		sql("update `tabPurchase Invoice` set outstanding_amount = 0 where fiscal_year=%s and company=%s", (self.doc.name, self.doc.company))
		sql("update `tabSales Invoice` set outstanding_amount = 0 where fiscal_year=%s and company=%s", (self.doc.name, self.doc.company))

	# Update Voucher Outstanding
	def update_voucher_outstanding(self):
		# Clear outstanding
		self.clear_outstanding()
		against_voucher = sql("select against_voucher, against_voucher_type from `tabGL Entry` where fiscal_year=%s and ifnull(is_cancelled, 'No')='No' and company=%s and ifnull(against_voucher, '') != '' and ifnull(against_voucher_type, '') != '' group by against_voucher, against_voucher_type", (self.doc.name, self.doc.company))
		for d in against_voucher:
			# get voucher balance
			bal = sql("select sum(debit)-sum(credit) from `tabGL Entry` where against_voucher=%s and against_voucher_type=%s and ifnull(is_cancelled, 'No') = 'No'", (d[0], d[1]))
			bal = bal and flt(bal[0][0]) or 0.0
			if d[1] == 'Purchase Invoice':
				bal = -bal
			# set voucher balance
			sql("update `tab%s` set outstanding_amount=%s where name='%s'"% (d[1], bal, d[0]))

	# ====================================================================================
	# Generate periods
	def create_periods(self):
		get_obj('Period Control').generate_periods(self.doc.name)

	def validate(self):
		if sql("select name from `tabFiscal Year` where year_start_date < %s", self.doc.year_start_date) and not self.doc.past_year:
			msgprint("Please enter Past Year", raise_exception=1)

		if not self.doc.is_fiscal_year_closed:
			self.doc.is_fiscal_year_closed = 'No'


	# on update
	def on_update(self):
		self.create_periods()
		self.create_account_balances()

		if self.doc.fields.get('localname', '')[:15] == 'New Fiscal Year':
			for d in sql("select name from tabCompany"):
				self.update_opening(d[0])
