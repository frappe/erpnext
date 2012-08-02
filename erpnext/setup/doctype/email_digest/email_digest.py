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

import webnotes
import webnotes.utils

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc, self.doclist = doc, doclist
		self.sending = False


	def get_profiles(self):
		"""
			Get a list of profiles
		"""
		import webnotes
		profile_list = webnotes.conn.sql("""
			SELECT name, enabled FROM tabProfile
			WHERE docstatus=0 AND name NOT IN ('Administrator', 'Guest')
			ORDER BY enabled DESC, name ASC""", as_dict=1)
		if self.doc.recipient_list:
			recipient_list = self.doc.recipient_list.split("\n")
		else:
			recipient_list = []
		for p in profile_list:
			if p['name'] in recipient_list: p['checked'] = 1
			else: p['checked'] = 0
		webnotes.response['profile_list'] = profile_list


	def get_standard_data(self):
		"""
			Executes standard queries
		"""
		res = {}
		query_dict = {

			'invoiced_amount': self.generate_gle_query({
				'type': 'invoiced_amount',
				'field': 'debit',
				'master_type': 'Customer',
			}),

			'payables': self.generate_gle_query({
				'type': 'payables',
				'field': 'credit',
				'master_type': 'Supplier',
			}),

			'collections': self.generate_gle_query({
				'type': 'collections',
				'field': 'credit',
				'master_type': 'Customer',
			}),

			'payments': self.generate_gle_query({
				'type': 'payments',
				'field': 'debit',
				'master_type': 'Supplier',
			}),

			'income': self.generate_gle_query({
				'type': 'income',
				'debit_or_credit': 'Credit'
			}),

			'income_year_to_date': self.generate_gle_query({
				'type': 'income_year_to_date',
				'debit_or_credit': 'Credit'
			}),

			'expenses_booked': self.generate_gle_query({
				'type': 'expenses_booked',
				'debit_or_credit': 'Debit'
			}),

			'bank_balance': self.generate_gle_query({
				'type': 'bank_balance'
			}),

			'new_leads': self.generate_new_type_query({
				'type': 'new_leads',
				'doctype': 'Lead'
			}),

			'new_enquiries': self.generate_new_type_query({
				'type': 'new_enquiries',
				'doctype': 'Opportunity'
			}),

			'new_quotations': self.generate_new_type_query({
				'type': 'new_quotations',
				'doctype': 'Quotation',
				'sum_col': 'grand_total'
			}),

			'new_sales_orders': self.generate_new_type_query({
				'type': 'new_sales_orders',
				'doctype': 'Sales Invoice',
				'sum_col': 'grand_total'
			}),

			'new_purchase_orders': self.generate_new_type_query({
				'type': 'new_purchase_orders',
				'doctype': 'Purchase Order',
				'sum_col': 'grand_total'
			}),

			'new_transactions': self.generate_new_type_query({
				'type': 'new_transactions',
				'doctype': 'Feed'
			}),

			'stock_below_rl': ""
		}

		result = {}

		for query in query_dict.keys():
			if self.doc.fields[query] and query_dict[query]:
				#webnotes.msgprint(query)
				res = webnotes.conn.sql(query_dict[query], as_dict=1)
				if query in ['income', 'income_year_to_date']:
					for r in res:
						r['value'] = float(r['credit'] - r['debit'])
				elif query in ['expenses_booked', 'bank_balance']:
					for r in res:
						r['value'] = float(r['debit'] - r['credit'])
				#webnotes.msgprint(query)
				#webnotes.msgprint(res)
				result[query] = res and (len(res)==1 and res[0]) or (res or None)
				if result[query] is None:
					del result[query]
		
		return result


	def generate_gle_query(self, args):
		"""
			Returns generated query string based 'tabGL Entry' and 'tabAccount'
		"""
		self.process_args(args)

		query = None

		if args['type'] in ['invoiced_amount', 'payables']:
			query = """
				SELECT
					IFNULL(SUM(IFNULL(gle.%(field)s, 0)), 0) AS '%(field)s',
					%(common_select)s
				FROM
					%(common_from)s
				WHERE
					%(common_where)s AND
					ac.master_type = '%(master_type)s' AND
					%(start_date_condition)s AND
					%(end_date_condition)s""" % args

		elif args['type'] in ['collections', 'payments']:
			args['bc_accounts_regex'] = self.get_bc_accounts_regex()
			if args['bc_accounts_regex']:
				query = """
					SELECT
						IFNULL(SUM(IFNULL(gle.%(field)s, 0)), 0) AS '%(field)s',
						%(common_select)s
					FROM
						%(common_from)s
					WHERE
						%(common_where)s AND
						ac.master_type = '%(master_type)s' AND
						gle.against REGEXP '%(bc_accounts_regex)s' AND
						%(start_date_condition)s AND
						%(end_date_condition)s""" % args

		elif args['type'] in ['income', 'expenses_booked']:
			query = """
				SELECT
					IFNULL(SUM(IFNULL(gle.debit, 0)), 0) AS 'debit',
					IFNULL(SUM(IFNULL(gle.credit, 0)), 0) AS 'credit',
					%(common_select)s
				FROM
					%(common_from)s
				WHERE
					%(common_where)s AND
					ac.is_pl_account = 'Yes' AND
					ac.debit_or_credit = '%(debit_or_credit)s' AND					
					%(start_date_condition)s AND
					%(end_date_condition)s""" % args

		elif args['type'] == 'income_year_to_date':
			query = """
				SELECT
					IFNULL(SUM(IFNULL(gle.debit, 0)), 0) AS 'debit',
					IFNULL(SUM(IFNULL(gle.credit, 0)), 0) AS 'credit',
					%(common_select)s
				FROM
					%(common_from)s
				WHERE
					%(common_where)s AND
					ac.is_pl_account = 'Yes' AND
					ac.debit_or_credit = '%(debit_or_credit)s' AND					
					%(fiscal_start_date_condition)s AND
					%(end_date_condition)s""" % args

		elif args['type'] == 'bank_balance':
			query = """
				SELECT
					ac.account_name AS 'name',
					IFNULL(SUM(IFNULL(gle.debit, 0)), 0) AS 'debit',
					IFNULL(SUM(IFNULL(gle.credit, 0)), 0) AS 'credit',
					%(common_select)s
				FROM
					%(common_from)s
				WHERE
					%(common_where)s AND
					ac.account_type = 'Bank or Cash' AND
					%(end_date_condition)s
				GROUP BY
					ac.account_name""" % args

		return query


	def process_args(self, args):
		"""
			Adds common conditions in dictionary "args"
		"""
		start_date, end_date = self.get_start_end_dates()
		fiscal_year = webnotes.utils.get_defaults()['fiscal_year']
		fiscal_start_date = webnotes.conn.get_value('Fiscal Year', fiscal_year,
				'year_start_date')

		if 'new' in args['type']:
			args.update({
				'company': self.doc.company,
				'start_date': start_date,
				'end_date': end_date,
				'sum_if_reqd': ''
			})
			if args['type'] in ['new_quotations', 'new_sales_orders', 'new_purchase_orders']:
				args['sum_if_reqd'] = "IFNULL(SUM(IFNULL(%(sum_col)s, 0)), 0) AS '%(sum_col)s'," % args
			
			if args['type'] == 'new_transactions':
				# tabFeed doesn't have company column
				# using this arg to set condition of feed_type as null
				# so that comments, logins and assignments are not counted
				args['company_condition'] = "feed_type IS NULL AND"
			else:
				args['company_condition'] = "company = '%(company)s' AND" % args
				
		else:
			args.update({
				'common_select': "COUNT(*) AS 'count'",

				'common_from': "`tabGL Entry` gle, `tabAccount` ac",

				'common_where': """
					gle.company = '%s' AND
					gle.account = ac.name AND
					ac.docstatus < 2 AND
					IFNULL(gle.is_cancelled, 'No') = 'No'""" % self.doc.company,

				'start_date_condition': "gle.posting_date >= '%s'" % start_date,

				'end_date_condition': "gle.posting_date <= '%s'" % end_date,

				'fiscal_start_date_condition': "gle.posting_date >= '%s'" % fiscal_start_date
			})


	def get_start_end_dates(self):
		"""
			Returns start and end date depending on the frequency of email digest
		"""
		from datetime import datetime, date, timedelta
		from webnotes.utils import now_datetime
		today = now_datetime().date()
		year, month, day = today.year, today.month, today.day
		
		if self.doc.frequency == 'Daily':
			if self.sending:
				start_date = end_date = today - timedelta(days=1)
			else:
				start_date = end_date = today
		
		elif self.doc.frequency == 'Weekly':
			if self.sending:
				start_date = today - timedelta(days=today.weekday(), weeks=1)
				end_date = start_date + timedelta(days=6)
			else:
				start_date = today - timedelta(days=today.weekday())
				end_date = start_date + timedelta(days=6)

		else:
			import calendar
			
			if self.sending:
				if month == 1:
					year = year - 1
					prev_month = 12
				else:
					prev_month = month - 1
				start_date = date(year, prev_month, 1)
				last_day = calendar.monthrange(year, prev_month)[1]
				end_date = date(year, prev_month, last_day)
			else:
				start_date = date(year, month, 1)
				last_day = calendar.monthrange(year, month)[1]
				end_date = date(year, month, last_day)

		return start_date, end_date


	def generate_new_type_query(self, args):
		"""
			Returns generated query string for calculating new transactions created
		"""
		self.process_args(args)

		query = """
			SELECT
				%(sum_if_reqd)s
				COUNT(*) AS 'count'
			FROM
				`tab%(doctype)s`
			WHERE
				docstatus < 2 AND
				%(company_condition)s
				DATE(creation) >= '%(start_date)s' AND
				DATE(creation) <= '%(end_date)s'""" % args

		return query
	
	
	def get_bc_accounts_regex(self):
		"""
			Returns a regular expression of 'Bank or Cash' type account list
		"""
		bc_account_list = webnotes.conn.sql("""
			SELECT name
			FROM `tabAccount`
			WHERE account_type = 'Bank or Cash'""", as_list=1)
		
		if bc_account_list:		
			return '(' + '|'.join([ac[0] for ac in bc_account_list]) + ')'
	

	def get(self):
		"""
			* Execute Query
			* Prepare Email Body from Print Format
		"""
		result, email_body = self.execute_queries()
		#webnotes.msgprint(result)
		#webnotes.msgprint(email_body)
		return result, email_body


	def execute_queries(self):
		"""
			* If standard==1, execute get_standard_data
			* If standard==0, execute python code in custom_code field
		"""
		result = {}
		if int(self.doc.use_standard)==1:
			result = self.get_standard_data()
			email_body = self.get_standard_body(result)
		else:
			result, email_body = self.execute_custom_code(self.doc)

		#webnotes.msgprint(result)

		return result, email_body


	def execute_custom_code(self, doc):
		"""
			Execute custom python code
		"""
		pass


	def send(self):
		"""
			* Execute get method
			* Send email to recipients
		"""
		if not self.doc.recipient_list: return

		self.sending = True
		result, email_body = self.get()
		
		recipient_list = self.doc.recipient_list.split("\n")

		# before sending, check if user is disabled or not
		# do not send if disabled
		profile_list = webnotes.conn.sql("SELECT name, enabled FROM tabProfile", as_dict=1)
		for profile in profile_list:
			if profile['name'] in recipient_list and profile['enabled'] == 0:
				del recipient_list[recipient_list.index(profile['name'])]

		from webnotes.utils.email_lib import sendmail
		try:
			sendmail(
				recipients=recipient_list,
				sender='notifications+email_digest@erpnext.com',
				reply_to='support@erpnext.com',
				subject=self.doc.frequency + ' Digest',
				msg=email_body
			)
		except Exception, e:
			webnotes.msgprint('There was a problem in sending your email. Please contact support@erpnext.com')
			webnotes.errprint(webnotes.getTraceback())


	def get_next_sending(self):
		import datetime
		
		start_date, end_date = self.get_start_end_dates()
		
		send_date = end_date + datetime.timedelta(days=1)
		
		from webnotes.utils import formatdate
		str_date = formatdate(str(send_date))

		self.doc.next_send = str_date + " at midnight"

		return send_date


	def onload(self):
		"""

		"""
		self.get_next_sending()


	def get_standard_body(self, result):
		"""
			Generate email body depending on the result
		"""
		from webnotes.utils import fmt_money
		from webnotes.model.doc import Document
		company = Document('Company', self.doc.company)
		currency = company.default_currency

		def table(args):
			table_body = ""
			
			if isinstance(args['body'], basestring):
				return """<p>%(head)s: <span style='font-size: 110%%; font-weight: bold;'>%(body)s</span></p>""" % args
			else:
				return ("""<p>%(head)s:</p> """ % args) +\
				 	"".join(map(lambda b: "<p style='margin-left: 17px;'>%s</p>" % b, args['body']))


		currency_amount_str = "<span style='color: grey;'>%s</span> %s"

		body_dict = {

			'invoiced_amount': {
				'table': result.get('invoiced_amount') and \
					table({
						'head': 'Invoiced Amount',
						'body': currency_amount_str \
							% (currency, fmt_money(result['invoiced_amount'].get('debit')))
					}),
				'idx': 300,
				'value': result.get('invoiced_amount') and result['invoiced_amount'].get('debit')
			},

			'payables': {
				'table': result.get('payables') and \
					table({
						'head': 'Payables',
						'body': currency_amount_str \
							% (currency, fmt_money(result['payables'].get('credit')))
					}),
				'idx': 200,
				'value': result.get('payables') and result['payables'].get('credit')
			},

			'collections': {
				'table': result.get('collections') and \
					table({
						'head': 'Collections',
						'body': currency_amount_str \
							% (currency, fmt_money(result['collections'].get('credit')))
					}),
				'idx': 301,
				'value': result.get('collections') and result['collections'].get('credit')
			},

			'payments': {
				'table': result.get('payments') and \
					table({
						'head': 'Payments',
						'body': currency_amount_str \
							% (currency, fmt_money(result['payments'].get('debit')))
					}),
				'idx': 201,
				'value': result.get('payments') and result['payments'].get('debit')
			},

			'income': {
				'table': result.get('income') and \
					table({
						'head': 'Income',
						'body': currency_amount_str \
							% (currency, fmt_money(result['income'].get('value')))
					}),
				'idx': 302,
				'value': result.get('income') and result['income'].get('value')
			},

			'income_year_to_date': {
				'table': result.get('income_year_to_date') and \
					table({
						'head': 'Income Year To Date',
						'body': currency_amount_str \
							% (currency, fmt_money(result['income_year_to_date'].get('value')))
					}),
				'idx': 303,
				'value': result.get('income_year_to_date') and \
				 	result['income_year_to_date'].get('value')
			},

			'expenses_booked': {
				'table': result.get('expenses_booked') and \
					table({
						'head': 'Expenses Booked',
						'body': currency_amount_str \
							% (currency, fmt_money(result['expenses_booked'].get('value')))
					}),
				'idx': 202,
				'value': result.get('expenses_booked') and result['expenses_booked'].get('value')
			},

			'bank_balance': {
				'table': result.get('bank_balance') and \
					table({
						'head': 'Bank / Cash Balance',
						'body': [(bank['name'] + ": <span style='font-size: 110%%; font-weight: bold;'>" \
									+ currency_amount_str % \
									(currency, fmt_money(bank.get('value'))) + '</span>')
							for bank in (isinstance(result['bank_balance'], list) and \
								result['bank_balance'] or \
								[result['bank_balance']])
						]
					}),
				'idx': 0,
				'value': 0.1
			},

			'new_leads': {
				'table': result.get('new_leads') and \
					table({
						'head': 'New Leads',
						'body': '%s' % result['new_leads'].get('count')
					}),
				'idx': 100,
				'value': result.get('new_leads') and result['new_leads'].get('count')
			},

			'new_enquiries': {
				'table': result.get('new_enquiries') and \
					table({
						'head': 'New Enquiries',
						'body': '%s' % result['new_enquiries'].get('count')
					}),
				'idx': 101,
				'value': result.get('new_enquiries') and result['new_enquiries'].get('count')
			},

			'new_quotations': {
				'table': result.get('new_quotations') and \
					table({
						'head': 'New Quotations',
						'body': '%s' % result['new_quotations'].get('count')
					}),
				'idx': 102,
				'value': result.get('new_quotations') and result['new_quotations'].get('count')
			},

			'new_sales_orders': {
				'table': result.get('new_sales_orders') and \
					table({
						'head': 'New Sales Orders',
						'body': '%s' % result['new_sales_orders'].get('count')
					}),
				'idx': 103,
				'value': result.get('new_sales_orders') and result['new_sales_orders'].get('count')
			},

			'new_purchase_orders': {
				'table': result.get('new_purchase_orders') and \
					table({
						'head': 'New Purchase Orders',
						'body': '%s' % result['new_purchase_orders'].get('count')
					}),
				'idx': 104,
				'value': result.get('new_purchase_orders') and \
				 	result['new_purchase_orders'].get('count')
			},

			'new_transactions': {
				'table': result.get('new_transactions') and \
					table({
						'head': 'New Transactions',
						'body': '%s' % result['new_transactions'].get('count')
					}),
				'idx': 105,
				'value': result.get('new_transactions') and result['new_transactions'].get('count')
			}

			#'stock_below_rl': 
		}

		table_list = []

		# Sort these keys depending on idx value
		bd_keys = sorted(body_dict, key=lambda x: \
			(-webnotes.utils.flt(body_dict[x]['value']), body_dict[x]['idx']))

		new_section = False

		def set_new_section(new_section):
			if not new_section:
				table_list.append("<hr /><h4>No Updates For:</h4><br>")
				new_section = True
			return new_section			

		for k in bd_keys:
			if self.doc.fields[k]:
				if k in result:
					if not body_dict[k].get('value') and not new_section:
						new_section = set_new_section(new_section)
					table_list.append(body_dict[k]['table'])
				elif k in ['collections', 'payments']:
					new_section = set_new_section(new_section)
					table_list.append(\
						"<p>[" + \
							k.capitalize() + \
							"]<br />Missing: Account of type 'Bank or Cash'\
						</p>")
				elif k=='bank_balance':
					new_section = set_new_section(new_section)
					table_list.append(\
						"<p>[" + \
							"Bank Balance" + \
							"]<br />Alert: GL Entry not found for Account of type 'Bank or Cash'\
						</p>")
					

		from webnotes.utils import formatdate
		start_date, end_date = self.get_start_end_dates()
		digest_daterange = self.doc.frequency=='Daily' \
			and formatdate(str(start_date)) \
			or (formatdate(str(start_date)) + " to " + (formatdate(str(end_date))))

		email_body = """
					<h2>%s</h2>
					<p style='color: grey'>%s</p>
					<h4>%s</h4>
					<hr>
				""" \
					% ((self.doc.frequency + " Digest"), \
						digest_daterange, self.doc.company) \
				+ "".join(table_list) + """\
				<br><p></p>
			"""

		return email_body


def send():
	"""

	"""
	edigest_list = webnotes.conn.sql("""
		SELECT name FROM `tabEmail Digest`
		WHERE enabled=1 and docstatus<2
	""", as_list=1)

	from webnotes.model.code import get_obj
	from webnotes.utils import now_datetime

	now_date = now_datetime().date()
	
	for ed in edigest_list:
		if ed[0]:
			ed_obj = get_obj('Email Digest', ed[0])
			ed_obj.sending = True
			send_date = ed_obj.get_next_sending()
			#webnotes.msgprint([ed[0], now_date, send_date])

			if (now_date == send_date):
				ed_obj.send()
