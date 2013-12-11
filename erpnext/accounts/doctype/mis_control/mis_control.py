# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt, get_first_day, get_last_day, has_common
import webnotes.defaults
from accounts.utils import get_balance_on

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
	def get_comp(self):
		ret = {}
		type = []

		ret['period'] = ['Annual','Half Yearly','Quarterly','Monthly']
		
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

		# get MIS Type on basis of roles of session user
		self.roles = webnotes.user.get_roles()
		if has_common(self.roles, ['Sales Manager']):
			type.append('Sales')
		if has_common(self.roles, ['Purchase Manager']):
			type.append('Purchase')
		ret['type'] = type
		return ret

	
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
		
		return self.return_data

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

	def define_periods(self, year, period):	
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