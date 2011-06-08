# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
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
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl

	# Validate mandatory
	#-------------------
	def check_mandatory(self):
		# Following fields are mandatory in GL Entry
		mandatory = ['account','remarks','voucher_type','voucher_no','fiscal_year','company']
		for k in mandatory:
			if not self.doc.fields.get(k):
				msgprint("%s is mandatory for GL Entry" % k)
				raise Exception
				
		# Zero value transaction is not allowed
		if not (flt(self.doc.debit) or flt(self.doc.credit)):
			msgprint("GL Entry: Debit or Credit amount is mandatory for %s" % self.doc.account)
			raise Exception
			
		# Debit and credit can not done at the same time
		if flt(self.doc.credit) != 0 and flt(self.doc.debit) != 0:
			msgprint("Sorry you cannot credit and debit under same account head.")
			raise Exception, "Validation Error."
		
	# Cost center is required only if transaction made against pl account
	#--------------------------------------------------------------------
	def pl_must_have_cost_center(self):
		if sql("select name from tabAccount where name=%s and is_pl_account='Yes'", self.doc.account):
			if not self.doc.cost_center and self.doc.voucher_type != 'Period Closing Voucher':
				msgprint("Error: Cost Center must be specified for PL Account: %s" % self.doc.account)
				raise Exception
		else: # not pl
			if self.doc.cost_center:
				self.doc.cost_center = ''
		
	# Account must be ledger, active and not freezed
	#-----------------------------------------------
	def validate_account_details(self, adv_adj):
		ret = sql("select group_or_ledger, docstatus, freeze_account, company from tabAccount where name=%s", self.doc.account)
		
		# 1. Checks whether Account type is group or ledger
		if ret and ret[0][0]=='Group':
			msgprint("Error: All accounts must be Ledgers. Account %s is a group" % self.doc.account)
			raise Exception

		# 2. Checks whether Account is active
		if ret and ret[0][1]==2:
			msgprint("Error: All accounts must be Active. Account %s moved to Trash" % self.doc.account)
			raise Exception
			
		# 3. Account has been freezed for other users except account manager
		if ret and ret[0][2]== 'Yes' and not adv_adj and not 'Accounts Manager' in webnotes.user.get_roles():
			msgprint("Error: Account %s has been freezed. Only Accounts Manager can do transaction against this account." % self.doc.account)
			raise Exception
			
		# 4. Check whether account is within the company
		if ret and ret[0][3] != self.doc.company:
			msgprint("Account: %s does not belong to the company: %s" % (self.doc.account, self.doc.company))
			raise Exception
			
	# Posting date must be in selected fiscal year and fiscal year is active
	#-------------------------------------------------------------------------
	def validate_posting_date(self):
		fy = sql("select docstatus, year_start_date from `tabFiscal Year` where name=%s ", self.doc.fiscal_year)
		ysd = fy[0][1]
		yed = get_last_day(get_first_day(ysd,0,11))
		pd = getdate(self.doc.posting_date)
		if fy[0][0] == 2:
			msgprint("Fiscal Year is not active. You can restore it from Trash")
			raise Exception
		if pd < ysd or pd > yed:
			msgprint("Posting date must be in the Selected Financial Year")
			raise Exception
			
	
	# Nobody can do GL Entries where posting date is before freezing date except authorized person
	#----------------------------------------------------------------------------------------------
	def check_freezing_date(self, adv_adj):
		if not adv_adj:
			acc_frozen_upto = get_value('Manage Account', None, 'acc_frozen_upto')
			if acc_frozen_upto:
				bde_auth_role = get_value( 'Manage Account', None,'bde_auth_role')
				if getdate(self.doc.posting_date) <= getdate(acc_frozen_upto) and not bde_auth_role in webnotes.user.get_roles():
					msgprint("You are not authorized to do/modify back dated accounting entries before %s." % getdate(acc_frozen_upto).strftime('%d-%m-%Y'), raise_exception=1)

	# create new bal if not exists
	#-----------------------------
	def create_new_balances(self, det):
		# check
		if sql("select count(t1.name) from `tabAccount Balance` t1, tabAccount t2 where t1.fiscal_year=%s and t2.lft <= %s and t2.rgt >= %s and t2.name = t1.account", (self.doc.fiscal_year, det[0][0], det[0][1]))[0][0] < 13*(cint(det[0][1]) - cint(det[0][0]) +1)/2:
			period_list = self.get_period_list()
			accounts = sql("select name from tabAccount where lft <= %s and rgt >= %s" % (det[0][0], det[0][1]))

			for p in period_list:
				for a in accounts:
					# check if missing
					if not sql("select name from `tabAccount Balance` where period=%s and account=%s and fiscal_year=%s", (p[0], a[0], self.doc.fiscal_year)):
						d = Document('Account Balance')
						d.account = a[0]
						d.period = p[0]
						d.start_date = p[1].strftime('%Y-%m-%d')
						d.end_date = p[2].strftime('%Y-%m-%d')
						d.fiscal_year = self.doc.fiscal_year
						d.debit = 0
						d.credit = 0
						d.opening = 0
						d.balance = 0
						d.save(1)

	# Post Balance
	# ------------
	def post_balance(self, acc, cancel):
		# get details
		det = sql("select lft, rgt, debit_or_credit from `tabAccount` where name='%s'" % acc)

		# amount to debit
		amt = flt(self.doc.debit) - flt(self.doc.credit)
		if det[0][2] == 'Credit': amt = -amt
		if cancel:
			debit = -1 * flt(self.doc.credit)
			credit = -1 * flt(self.doc.debit)
		else:
			debit = flt(self.doc.debit)
			credit = flt(self.doc.credit)
		
		self.create_new_balances(det)
		
		# build dict
		p = {
			'debit': flt(debit)
			,'credit':flt(credit)
			,'opening': self.doc.is_opening=='Yes' and amt or 0
			# end date condition only if it is not opening
			,'end_date_condition':(self.doc.is_opening!='Yes' and ("and ab.end_date >= '"+self.doc.posting_date+"'") or '')
			,'diff': amt
			,'lft': cint(det[0][0])
			,'rgt': cint(det[0][1])
			,'posting_date': self.doc.posting_date
			,'fiscal_year': self.doc.fiscal_year
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

			
	# Get periods(month and year)
	#-----------------------------
	def get_period_list(self):
		pl = sql("SELECT name, start_date, end_date, fiscal_year FROM tabPeriod WHERE fiscal_year = '%s' and period_type in ('Month', 'Year')" % (self.doc.fiscal_year))
		return pl

	# Voucher Balance
	# ---------------	
	def update_outstanding_amt(self):
		# get final outstanding amt

		bal = flt(sql("select sum(debit)-sum(credit) from `tabGL Entry` where against_voucher=%s and against_voucher_type=%s and ifnull(is_cancelled,'No') = 'No'", (self.doc.against_voucher, self.doc.against_voucher_type))[0][0] or 0.0)
		tds = 0
		
		if self.doc.against_voucher_type=='Payable Voucher':
			# amount to debit
			bal = -bal
			
			# Check if tds applicable
			tds = sql("select total_tds_on_voucher from `tabPayable Voucher` where name = '%s'" % self.doc.against_voucher)
			tds = tds and flt(tds[0][0]) or 0
		
		# Validation : Outstanding can not be negative
		if bal < 0 and not tds and self.doc.is_cancelled == 'No':
			msgprint("Outstanding for Voucher %s will become %s. Outstanding cannot be less than zero. Please match exact outstanding." % (self.doc.against_voucher, fmt_money(bal)))
			raise Exception
			
		# Update outstanding amt on against voucher
		sql("update `tab%s` set outstanding_amount=%s where name='%s'"% (self.doc.against_voucher_type,bal,self.doc.against_voucher))
		
					
	# Total outstanding can not be greater than credit limit for any time for any customer
	#---------------------------------------------------------------------------------------------
	def check_credit_limit(self):
		#check for user role Freezed
		master_type=sql("select master_type, master_name from `tabAccount` where name='%s' " %self.doc.account)
		tot_outstanding = 0	#needed when there is no GL Entry in the system for that acc head
		if (self.doc.voucher_type=='Journal Voucher' or self.doc.voucher_type=='Receivable Voucher') and (master_type and master_type[0][0]=='Customer' and master_type[0][1]):
			dbcr = sql("select sum(debit),sum(credit) from `tabGL Entry` where account = '%s' and is_cancelled='No'" % self.doc.account)
			if dbcr:
				tot_outstanding = flt(dbcr[0][0])-flt(dbcr[0][1])+flt(self.doc.debit)-flt(self.doc.credit)
			get_obj('Account',self.doc.account).check_credit_limit(self.doc.account, self.doc.company, tot_outstanding)
	
	#for opening entry account can not be pl account
	#-----------------------------------------------
	def check_pl_account(self):
		if self.doc.is_opening=='Yes':
			is_pl_account=sql("select is_pl_account from `tabAccount` where name='%s'"%(self.doc.account))
			if is_pl_account and is_pl_account[0][0]=='Yes':
				msgprint("For opening balance entry account can not be a PL account")
				raise Exception

	# Validate
	# --------
	def validate(self):	# not called on cancel
		self.check_mandatory()
		self.pl_must_have_cost_center()
		self.validate_posting_date()
		self.doc.is_cancelled = 'No' # will be reset by GL Control if cancelled
		self.check_credit_limit()
		self.check_pl_account()

	# On Update
	#----------
	def on_update(self,adv_adj, cancel, update_outstanding = 'Yes'):
		# Account must be ledger, active and not freezed
		self.validate_account_details(adv_adj)
		
		# Posting date must be after freezing date
		self.check_freezing_date(adv_adj)
		
		# Update current account balance
		self.post_balance(self.doc.account, cancel)
		
		# Update outstanding amt on against voucher
		if self.doc.against_voucher and self.doc.against_voucher_type not in ('Journal Voucher','POS') and update_outstanding == 'Yes':
			self.update_outstanding_amt()
