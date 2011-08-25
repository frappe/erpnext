dashboards = [
	{
		'type': 'account',
		'account': 'Income',
		'title': 'Income'
	},
	
	{
		'type': 'account',
		'account': 'Expenses',
		'title': 'Expenses'
	},

	{
		'type': 'from_company',
		'account': 'receivables_group',
		'title': 'Receivables'
	},

	{
		'type': 'from_company',
		'account': 'payables_group',
		'title': 'Payables'
	},

	{
		'type': 'cash',
		'debit_or_credit': 'Debit',
		'title': 'Cash Inflow'
	},

	{
		'type': 'cash',
		'debit_or_credit': 'Credit',
		'title': 'Cash Outflow'
	},

	{
		'type': 'creation',
		'doctype': 'Quotation',
		'title': 'New Quotations'
	},
	
	{
		'type': 'creation',
		'doctype': 'Sales Order',
		'title': 'New Orders'
	}
]


class DashboardWidget:
	def __init__(self, company, start, end, interval):
		import webnotes
		from webnotes.utils import getdate
		from webnotes.model.code import get_obj
		
		self.company = company
		self.abbr = webnotes.conn.get_value('Company', company, 'abbr')
		self.start = getdate(start)
		self.end = getdate(end)
		
		self.interval = interval
		self.fiscal_year = webnotes.conn.sql("""
			select name from `tabFiscal Year` 
			where year_start_date <= %s and
			DATE_ADD(year_start_date, INTERVAL 1 YEAR) >= %s
			""", (start, start))[0][0]
		self.glc = get_obj('GL Control')
		self.cash_accounts = [d[0] for d in webnotes.conn.sql("""
			select name from tabAccount 
			where account_type='Bank or Cash'
			and company = %s and docstatus = 0 
			""", company)]
		
	def timeline(self):
		"""
			get the timeline for the dashboard
		"""
		import webnotes
		from webnotes.utils import add_days
		tl = []
	
		if self.start > self.end:
			webnotes.msgprint("Start must be before end", raise_exception=1)

		curr = self.start
		tl.append(curr)
	
		while curr < self.end:
			curr = add_days(curr, self.interval, 'date')
			tl.append(curr)

		tl.append(self.end)

		return tl
		
	def generate(self, opts):
		"""
			Generate the dasboard
		"""
		tl = self.timeline()
		self.out = []
		
		for i in range(len(tl)-1):
			self.out.append([tl[i+1].strftime('%Y-%m-%d'), self.value(opts, tl[i], tl[i+1]) or 0])
			
		return self.out

	def get_account_balance(self, acc, start):
		"""
			Get as on account balance
		"""
		import webnotes
		# add abbreviation to company
		
		if not acc.endswith(self.abbr):
			acc += ' - ' + self.abbr

		# get other reqd parameters
		try:
			globals().update(webnotes.conn.sql('select debit_or_credit, lft, rgt from tabAccount where name=%s', acc, as_dict=1)[0])
		except Exception,e:
			webnotes.msgprint('Wrongly defined account: ' + acc)
			print acc
			raise e
		
		return self.glc.get_as_on_balance(acc, self.fiscal_year, start, debit_or_credit, lft, rgt)

	def get_creation_trend(self, doctype, start, end):
		"""
			Get creation # of creations in period
		"""
		import webnotes
		return int(webnotes.conn.sql("""
			select count(*) from `tab%s` where creation between %s and %s and docstatus=1
		""" % (doctype, '%s','%s'), (start, end))[0][0])

	def get_account_amt(self, acc, start, end):
		"""
			Get debit, credit over a period
		"""
		import webnotes
		# add abbreviation to company
		
		if not acc.endswith(self.abbr):
			acc += ' - ' + self.abbr
			
		ret = webnotes.conn.sql("""
			select ifnull(sum(ifnull(t1.debit,0)),0), ifnull(sum(ifnull(t1.credit,0)),0)
			from `tabGL Entry` t1, tabAccount t2
			where t1.account = t2.name
			and t2.is_pl_account = 'Yes'
			and t2.debit_or_credit=%s
			and ifnull(t1.is_cancelled, 'No')='No'
			and t1.posting_date between %s and %s
		""", (acc=='Income' and 'Credit' or 'Debit', start, end))[0]
		
		return acc=='Income' and (ret[1]-ret[0]) or (ret[0]-ret[1])

	def value(self, opts, start, end):
		"""
			Value of the series on a particular date
		"""
		import webnotes
		if opts['type']=='account':
			bal = self.get_account_amt(opts['account'], start, end)
		
		elif opts['type']=='from_company':
			acc = webnotes.conn.get_value('Company', self.company, \
				opts['account'].split('.')[-1])
			
			return self.get_account_balance(acc, start)[2]
						
		elif opts['type']=='cash':
			if opts['debit_or_credit']=='Credit':
				return sum([self.get_account_balance(acc, start)[1] for acc in self.cash_accounts]) or 0
			elif opts['debit_or_credit']=='Debit':
				return sum([self.get_account_balance(acc, start)[0] for acc in self.cash_accounts]) or 0
			
		elif opts['type']=='creation':
			return self.get_creation_trend(opts['doctype'], start, end)


def load_dashboard(args):
	"""
		Get dashboard based on
		1. Company (default company)
		2. Start Date (last 3 months)
		3. End Date (today)
		4. Interval (7 days)
	"""
	dl = []
	import json
	args = json.loads(args)
	dw = DashboardWidget(args['company'], args['start'], args['end'], int(args['interval']))

	# render the dashboards
	for d in dashboards:
		dl.append([d, dw.generate(d)])

	return dl

if __name__=='__main__':
	import sys
	sys.path.append('/var/www/webnotes/wnframework/cgi-bin')
	from webnotes.db import Database
	import webnotes
	webnotes.conn = Database(use_default=1)
	webnotes.session = {'user':'Administrator'}
	print load_dashboard("""{
		"company": "My Test",
		"start": "2011-05-01",
		"end": "2011-08-01",
		"interval": "7"
	}""")