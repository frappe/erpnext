dashboards = [
	{
		'type': 'account',
		'account': 'Income',
		'title': 'Income',
		'fillColor': '#90EE90'
	},
	
	{
		'type': 'account',
		'account': 'Expenses',
		'title': 'Expenses',
		'fillColor': '#90EE90'
	},

	{
		'type': 'receivables',
		'title': 'Receivables',
		'fillColor': '#FFE4B5'
	},

	{
		'type': 'payables',
		'title': 'Payables',
		'fillColor': '#FFE4B5'
	},

	{
		'type': 'collection',
		'title': 'Collection',
		'comment':'This info comes from the accounts your have marked as "Bank or Cash"',
		'fillColor': '#DDA0DD'
	},

	{
		'type': 'payments',
		'title': 'Payments',
		'comment':'This info comes from the accounts your have marked as "Bank or Cash"',
		'fillColor': '#DDA0DD'
	},

	{
		'type': 'creation',
		'doctype': 'Quotation',
		'title': 'New Quotations',
		'fillColor': '#ADD8E6'
	},
	
	{
		'type': 'creation',
		'doctype': 'Sales Order',
		'title': 'New Orders',
		'fillColor': '#ADD8E6'
	}
]

class DashboardWidget:
	def __init__(self, company, start, end, interval):
		from webnotes.utils import getdate
		from webnotes.model.code import get_obj
		import webnotes
		
		self.company = company
		self.abbr = webnotes.conn.get_value('Company', company, 'abbr')
		self.start = getdate(start)
		self.end = getdate(end)
		
		self.interval = interval

		self.glc = get_obj('GL Control')
		self.cash_accounts = [d[0] for d in webnotes.conn.sql("""
			select name from tabAccount 
			where account_type='Bank or Cash'
			and company = %s and docstatus = 0 
			""", company)]
			
		self.receivables_group = webnotes.conn.get_value('Company', company,'receivables_group')
		self.payables_group = webnotes.conn.get_value('Company', company,'payables_group')
		
		# list of bank and cash accounts
		self.bc_list = [s[0] for s in webnotes.conn.sql("select name from tabAccount where account_type='Bank or Cash'")]

		
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
		from webnotes.utils import flt
		tl = self.timeline()
		self.out = []
		
		for i in range(len(tl)-1):
			self.out.append([tl[i+1].strftime('%Y-%m-%d'), flt(self.value(opts, tl[i], tl[i+1])) or 0])
			
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
		
		return self.glc.get_as_on_balance(acc, self.get_fiscal_year(start), start, debit_or_credit, lft, rgt)

	def get_fiscal_year(self, dt):
		"""
			get fiscal year from date
		"""
		import webnotes
		return webnotes.conn.sql("""
			select name from `tabFiscal Year` 
			where year_start_date <= %s and
			DATE_ADD(year_start_date, INTERVAL 1 YEAR) >= %s
			""", (dt, dt))[0][0]
			
	def get_creation_trend(self, doctype, start, end):
		"""
			Get creation # of creations in period
		"""
		import webnotes
		return int(webnotes.conn.sql("""
			select count(*) from `tab%s` where creation between %s and %s and docstatus=1
		""" % (doctype, '%s','%s'), (start, end))[0][0])

	def get_account_amt(self, acc, start, end, debit_or_credit):
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
		""", (debit_or_credit, start, end))[0]
		
		return debit_or_credit=='Credit' and float(ret[1]-ret[0]) or float(ret[0]-ret[1])

	def get_bank_amt(self, debit_or_credit, master_type, start, end):
		"""
			Get collection (reduction in receivables over a period)
		"""
		import webnotes

		reg = '('+'|'.join(self.bc_list) + ')'

		return webnotes.conn.sql("""
		select sum(t1.%s)
		from `tabGL Entry` t1, tabAccount t2
		where t1.account = t2.name
		and t2.master_type='%s'
		and t1.%s > 0
		and t1.against REGEXP '%s'
		and ifnull(t1.is_cancelled, 'No')='No'
		and t1.posting_date between '%s' and '%s'
		""" % (debit_or_credit, master_type, debit_or_credit, reg, start, end))[0][0]


	def value(self, opts, start, end):
		"""
			Value of the series on a particular date
		"""
		import webnotes
		if opts['type']=='account':
			debit_or_credit = 'Debit'
			if opts['account']=='Income':
				debit_or_credit = 'Credit'

			return self.get_account_amt(opts['account'], start, end, debit_or_credit)
		
		elif opts['type']=='receivables':
			return self.get_account_balance(self.receivables_group, end)[2]
			
		elif opts['type']=='payables':
			return self.get_account_balance(self.payables_group, end)[2]

		elif opts['type']=='collection':
			return self.get_bank_amt('credit', 'Customer', start, end)

		elif opts['type']=='payments':
			return self.get_bank_amt('debit', 'Supplier', start, end)
			
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