# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, flt, getdate
from webnotes import msgprint

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl
		
	# Get monthly budget
	#-------------------
	def get_monthly_budget(self, distribution_id, cfy, st_date, post_dt, budget_allocated):
		
		# get month_list
		st_date, post_dt = getdate(st_date), getdate(post_dt)
		
		if distribution_id:
			if st_date.month <= post_dt.month:
				tot_per_allocated = webnotes.conn.sql("select ifnull(sum(percentage_allocation),0) from `tabBudget Distribution Detail` where parent='%s' and idx between '%s' and '%s'" % (distribution_id, st_date.month, post_dt.month))[0][0]

			if st_date.month > post_dt.month:
		
				tot_per_allocated = flt(webnotes.conn.sql("select ifnull(sum(percentage_allocation),0) from `tabBudget Distribution Detail` where parent='%s' and idx between '%s' and '%s'" % (distribution_id, st_date.month, 12 ))[0][0])
				tot_per_allocated = flt(tot_per_allocated)	+ flt(webnotes.conn.sql("select ifnull(sum(percentage_allocation),0) from `tabBudget Distribution Detail` where parent='%s' and idx between '%s' and '%s'" % (distribution_id, 1, post_dt.month))[0][0])
		 
			return (flt(budget_allocated) * flt(tot_per_allocated)) / 100
		period_diff = webnotes.conn.sql("select PERIOD_DIFF('%s','%s')" % (post_dt.strftime('%Y%m'), st_date.strftime('%Y%m')))
		
		return (flt(budget_allocated) * (flt(period_diff[0][0]) + 1)) / 12
		
	def validate_budget(self, acct, cost_center, actual, budget, action):
		# action if actual exceeds budget
		if flt(actual) > flt(budget):
			msgprint("Your monthly expense "+ cstr((action == 'stop') and "will exceed" or "has exceeded") +" budget for <b>Account - "+cstr(acct)+" </b> under <b>Cost Center - "+ cstr(cost_center) + "</b>"+cstr((action == 'Stop') and ", you can not have this transaction." or "."))
			if action == 'Stop': raise Exception

	def check_budget(self,gle,cancel):
		# get allocated budget
		
		bgt = webnotes.conn.sql("""select t1.budget_allocated, t1.actual, t2.distribution_id 
			from `tabBudget Detail` t1, `tabCost Center` t2 
			where t1.account='%s' and t1.parent=t2.name and t2.name = '%s' 
			and t1.fiscal_year='%s'""" % 
			(gle['account'], gle['cost_center'], gle['fiscal_year']), as_dict =1)

		curr_amt = flt(gle['debit']) - flt(gle['credit'])
		if cancel: curr_amt = -1 * curr_amt
		
		if bgt and bgt[0]['budget_allocated']:
			# check budget flag in Company
			bgt_flag = webnotes.conn.sql("""select yearly_bgt_flag, monthly_bgt_flag 
				from `tabCompany` where name = '%s'""" % gle['company'], as_dict =1)
			
			if bgt_flag and bgt_flag[0]['monthly_bgt_flag'] in ['Stop', 'Warn']:
				# get start date and last date
				start_date = webnotes.conn.get_value('Fiscal Year', gle['fiscal_year'], \
				 	'year_start_date').strftime('%Y-%m-%d')
				end_date = webnotes.conn.sql("select LAST_DAY('%s')" % gle['posting_date'])
			
				# get Actual
				actual = self.get_period_difference(gle['account'] + 
					'~~~' + cstr(start_date) + '~~~' + cstr(end_date[0][0]), gle['cost_center'])
		
				# Get Monthly	budget
				budget = self.get_monthly_budget(bgt and bgt[0]['distribution_id'] or '' , \
					gle['fiscal_year'], start_date, gle['posting_date'], bgt[0]['budget_allocated'])
		
				# validate monthly budget
				self.validate_budget(gle['account'], gle['cost_center'], \
					flt(actual) + flt(curr_amt), budget, bgt_flag[0]['monthly_bgt_flag'])

			# update actual against budget allocated in cost center
			webnotes.conn.sql("""update `tabBudget Detail` set actual = ifnull(actual,0) + %s 
				where account = '%s' and fiscal_year = '%s' and parent = '%s'""" % 
				(curr_amt, gle['account'],gle['fiscal_year'], gle['cost_center']))


	def get_period_difference(self, arg, cost_center =''):
		# used in General Ledger Page Report
		# used for Budget where cost center passed as extra argument
		acc, f, t = arg.split('~~~')
		c, fy = '', webnotes.conn.get_defaults()['fiscal_year']

		det = webnotes.conn.sql("select debit_or_credit, lft, rgt, is_pl_account from tabAccount where name=%s", acc)
		if f: c += (' and t1.posting_date >= "%s"' % f)
		if t: c += (' and t1.posting_date <= "%s"' % t)
		if cost_center: c += (' and t1.cost_center = "%s"' % cost_center)
		bal = webnotes.conn.sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) from `tabGL Entry` t1 where t1.account='%s' %s" % (acc, c))
		bal = bal and flt(bal[0][0]) or 0

		if det[0][0] != 'Debit':
			bal = (-1) * bal

		return flt(bal)