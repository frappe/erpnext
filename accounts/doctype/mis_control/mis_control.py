# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, cstr, flt, get_first_day, get_last_day, has_common
from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist
from webnotes import session, msgprint

import webnotes.defaults


from accounts.utils import get_balance_on, get_fiscal_year

class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist
		self.account_list = []
		self.ac_details = {} # key: account id, values: debit_or_credit, lft, rgt
		
		self.period_list = []
		self.period_start_date = {}
		self.period_end_date = {}

		self.fs_list = []
		self.root_bal = []
		self.flag = 0
		
	# Get defaults on load of MIS, MIS - Comparison Report and Financial statements
	# ----------------------------------------------------
	def get_comp(self):
		ret = {}
		type = []
		comp = []
		# ------ get period -----------
		ret['period'] = ['Annual','Half Yearly','Quarterly','Monthly']
		
		# ---- get companies ---------
		from accounts.page.accounts_browser.accounts_browser import get_companies
		ret['company'] = get_companies()

		#--- to get fiscal year and start_date of that fiscal year -----
		res = webnotes.conn.sql("select name, year_start_date from `tabFiscal Year`")
		ret['fiscal_year'] = [r[0] for r in res]
		ret['start_dates'] = {}
		for r in res:
			ret['start_dates'][r[0]] = str(r[1])
			
		#--- from month and to month (for MIS - Comparison Report) -------
		month_list = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
		fiscal_start_month = webnotes.conn.sql("select MONTH(year_start_date) from `tabFiscal Year` where name = %s",(webnotes.defaults.get_global_default("fiscal_year")))
		fiscal_start_month = fiscal_start_month and fiscal_start_month[0][0] or 1
		mon = ['']
		for i in range(fiscal_start_month,13): mon.append(month_list[i-1])
		for i in range(0,fiscal_start_month-1): mon.append(month_list[i])
		ret['month'] = mon

		# ------------------------ get MIS Type on basis of roles of session user ------------------------------------------
		self.roles = webnotes.user.get_roles()
		if has_common(self.roles, ['Sales Manager']):
			type.append('Sales')
		if has_common(self.roles, ['Purchase Manager']):
			type.append('Purchase')
		ret['type'] = type
		return ret
		
	# Gets Transactions type and Group By options based on module
	#------------------------------------------------------------------
	def get_trans_group(self,module):
		ret = {}
		st,group = [],[]
		if module == 'Sales':
			st = ['Quotation','Sales Order','Delivery Note','Sales Invoice']
			group = ['Item','Item Group','Customer','Customer Group','Cost Center']
		elif module == 'Purchase':
			st = ['Purchase Order','Purchase Receipt','Purchase Invoice']
			group = ['Item','Item Group','Supplier','Supplier Type']
		
		ret['stmt_type'] = st
		ret['group_by'] = group
		
		return ret

	# Get Days based on month (for MIS Comparison Report)
	# --------------------------------------------------------
	def get_days(self,month):
		days = []
		ret = {}
		if month == 'Jan' or month == 'Mar' or month == 'May' or month == 'Jul' or month == 'Aug' or month == 'Oct' or month == 'Dec':
			for i in range(1,32):
				days.append(i)
		elif month == 'Apr' or month == 'Jun' or month == 'Sep' or month == 'Nov':
			for i in range(1,31):
				days.append(i)
		elif month == 'Feb':
			for i in range(1,29):
				days.append(i)
		ret['days'] = days
		return ret
	
	# Get from date and to date based on fiscal year (for in summary - comparison report)
	# -----------------------------------------------------------------------------------------------------
	def dates(self,fiscal_year,from_date,to_date):
		import datetime
		ret = ''
		start_date = cstr(webnotes.conn.sql("select year_start_date from `tabFiscal Year` where name = %s",fiscal_year)[0][0])
		st_mon = cint(from_date.split('-')[1])
		ed_mon = cint(to_date.split('-')[1])
		st_day = cint(from_date.split('-')[2])
		ed_day = cint(to_date.split('-')[2])
		fiscal_start_month = cint(start_date.split('-')[1])
		next_fiscal_year = cint(start_date.split('-')[0]) + 1
		current_year = ''
		next_year = ''
		
		#CASE - 1 : Jan - Mar (Valid)
		if st_mon < fiscal_start_month and ed_mon < fiscal_start_month:
			current_year = cint(start_date.split('-')[0]) + 1
			next_year	= cint(start_date.split('-')[0]) + 1
		
		# Case - 2 : Apr - Dec (Valid)
		elif st_mon >= fiscal_start_month and ed_mon <= 12 and ed_mon >= fiscal_start_month:
			current_year = cint(start_date.split('-')[0])
			next_year	= cint(start_date.split('-')[0])

		# Case 3 : Jan - May (Invalid)
		elif st_mon < fiscal_start_month and ed_mon >= fiscal_start_month:
			current_year = cint(start_date.split('-')[0]) + 1
			next_year	= cint(start_date.split('-')[0]) + 2
	
		# check whether from date is within fiscal year
		if datetime.date(current_year, st_mon, st_day) >= datetime.date(cint(start_date.split('-')[0]), cint(start_date.split('-')[1]), cint(start_date.split('-')[2])) and datetime.date(cint(current_year), cint(st_mon), cint(st_day)) < datetime.date((cint(start_date.split('-')[0])+1), cint(start_date.split('-')[1]), cint(start_date.split('-')[2])):
			begin_date = cstr(current_year)+"-"+cstr(st_mon)+"-"+cstr(st_day)
		else:
			msgprint("Please enter appropriate from date.")
			raise Exception
		# check whether to date is within fiscal year
		if datetime.date(next_year, ed_mon, ed_day) >= datetime.date(cint(start_date.split('-')[0]), cint(start_date.split('-')[1]), cint(start_date.split('-')[2])) and datetime.date(cint(next_year), cint(ed_mon), cint(ed_day)) < datetime.date(cint(start_date.split('-')[0])+1, cint(start_date.split('-')[1]), cint(start_date.split('-')[2])):
			end_date = cstr(next_year)+"-"+cstr(ed_mon)+"-"+cstr(ed_day)
		else:
			msgprint("Please enter appropriate to date.")
			raise Exception
		ret = begin_date+'~~~'+end_date
		return ret

	# Get MIS Totals
	# ---------------
	def get_totals(self, args):
		args = eval(args)
		#msgprint(args)
		totals = webnotes.conn.sql("SELECT %s FROM %s WHERE %s %s %s %s" %(cstr(args['query_val']), cstr(args['tables']), cstr(args['company']), cstr(args['cond']), cstr(args['add_cond']), cstr(args['fil_cond'])), as_dict = 1)[0]
		#msgprint(totals)
		tot_keys = totals.keys()
		# return in flt because JSON doesn't accept Decimal
		for d in tot_keys:
			totals[d] = flt(totals[d])
		return totals

	# Get Statement
	# -------------
	
	def get_statement(self, arg): 
		self.return_data = []		

		# define periods
		arg = eval(arg)
		pl = ''
		
		self.define_periods(arg['year'], arg['period'])
		self.return_data.append([4,'']+self.period_list)

				
		if arg['statement'] == 'Balance Sheet': pl = 'No'
		if arg['statement'] == 'Profit & Loss': pl = 'Yes'
		self.get_children('',0,pl,arg['company'], arg['year'])
				
		#self.balance_pl_statement(acct, arg['statement'])
		#msgprint(self.return_data)
		return self.return_data
		
	# Get Children
	# ------------
	def get_children(self, parent_account, level, pl, company, fy):
		cl = webnotes.conn.sql("select distinct account_name, name, debit_or_credit, lft, rgt from `tabAccount` where ifnull(parent_account, '') = %s and ifnull(is_pl_account, 'No')=%s and company=%s and docstatus != 2 order by name asc", (parent_account, pl, company))
		level0_diff = [0 for p in self.period_list]
		if pl=='Yes' and level==0: # switch for income & expenses
			cl = [c for c in cl]
			cl.reverse()
		if cl:
			for c in cl:
				self.ac_details[c[1]] = [c[2], c[3], c[4]]
				bal_list = self.get_period_balance(c[1], pl)
				if level==0: # top level - put balances as totals
					self.return_data.append([level, c[0]] + ['' for b in bal_list])
					totals = bal_list
					for i in range(len(totals)): # make totals
						if c[2]=='Credit':
							level0_diff[i] += flt(totals[i])
						else:
							level0_diff[i] -= flt(totals[i])
				else:
					self.return_data.append([level, c[0]]+bal_list)
					
				if level < 2:
					self.get_children(c[1], level+1, pl, company, fy)
					
				# make totals - for top level
				# ---------------------------
				if level==0:
					# add rows for profit / loss in B/S
					if pl=='No':
						if c[2]=='Credit':
							self.return_data.append([1, 'Total Liabilities'] + totals)
							level0_diff = [-i for i in level0_diff] # convert to debit
							self.return_data.append([5, 'Profit/Loss (Provisional)'] + level0_diff)
							for i in range(len(totals)): # make totals
								level0_diff[i] = flt(totals[i]) + level0_diff[i]
						else:
							self.return_data.append([4, 'Total '+c[0]] + totals)

					# add rows for profit / loss in P/L
					else:
						if c[2]=='Debit':
							self.return_data.append([1, 'Total Expenses'] + totals)
							self.return_data.append([5, 'Profit/Loss (Provisional)'] + level0_diff)
							for i in range(len(totals)): # make totals
								level0_diff[i] = flt(totals[i]) + level0_diff[i]
						else:
							self.return_data.append([4, 'Total '+c[0]] + totals)
	
	# Define Periods
	# --------------
	
	def define_periods(self, year, period):
		
		# get year start date		
		ysd = webnotes.conn.sql("select year_start_date from `tabFiscal Year` where name=%s", year)
		ysd = ysd and ysd[0][0] or ''

		self.ysd = ysd

		# year
		if period == 'Annual':
			pn = 'FY'+year
			self.period_list.append(pn)
			self.period_start_date[pn] = ysd
			self.period_end_date[pn] = get_last_day(get_first_day(ysd,0,11))

		# quarter
		if period == 'Quarterly':
			for i in range(4):
				pn = 'Q'+str(i+1)
				self.period_list.append(pn)
			
				self.period_start_date[pn] = get_first_day(ysd,0,i*3)
				self.period_end_date[pn] = get_last_day(get_first_day(ysd,0,((i+1)*3)-1))	

		# month
		if period == 'Monthly':
			mlist = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
			for i in range(12):
				fd = get_first_day(ysd,0,i)
				pn = mlist[fd.month-1]
				self.period_list.append(pn)
			
				self.period_start_date[pn] = fd
				self.period_end_date[pn] = get_last_day(fd)
			
	def get_period_balance(self, acc, pl):
		ret, i = [], 0
		for p in self.period_list:
			period_end_date = self.period_end_date[p].strftime('%Y-%m-%d')
			bal = get_balance_on(acc, period_end_date)
			if pl=='Yes': 
				bal = bal - sum(ret)
				
			ret.append(bal)
		return ret