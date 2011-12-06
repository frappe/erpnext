import webnotes

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
				'doctype': 'Enquiry'
			}),

			'new_quotations': self.generate_new_type_query({
				'type': 'new_quotations',
				'doctype': 'Quotation',
				'sum_col': 'grand_total'
			}),

			'new_sales_orders': self.generate_new_type_query({
				'type': 'new_sales_orders',
				'doctype': 'Receivable Voucher',
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
			if self.doc.fields[query]:
				#webnotes.msgprint(query)
				res = webnotes.conn.sql(query_dict[query], as_dict=1, debug=1)
				if query == 'income':
					for r in res:
						r['value'] = float(r['credit'] - r['debit'])
				elif query in ['expenses_booked', 'bank_balance']:
					for r in res:
						r['value'] = float(r['debit'] - r['credit'])
				#webnotes.msgprint(query)
				#webnotes.msgprint(res)
				result[query] = (res and res[0]) and res[0] or None

		#webnotes.msgprint(result)
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

		elif args['type'] == 'bank_balance':
			query = """
				SELECT
					ac.name AS 'name',
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
					ac.name""" % args

		return query


	def process_args(self, args):
		"""
			Adds common conditions in dictionary "args"
		"""
		start_date, end_date = self.get_start_end_dates()

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
				args['company_condition'] = ''
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

				'end_date_condition': "gle.posting_date <= '%s'" % end_date
			})


	def get_start_end_dates(self):
		"""
			Returns start and end date depending on the frequency of email digest
		"""
		from datetime import datetime, date, timedelta
		today = datetime.now().date()
		year, month, day = today.year, today.month, today.day
		
		if self.doc.frequency == 'Daily':
			if self.sending:
				start_date = end_date = today - timedelta(days=1)
			else:
				start_date = end_date = today
		
		elif self.doc.frequency == 'Weekly':
			if self.sending:
				start_date = today - timedelta(weeks=1)
				end_date = today - timedelta(days=1)
			else:
				start_date = today - timedelta(days=today.weekday())
				end_date = start_date + timedelta(weeks=1)

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
				creation >= '%(start_date)s' AND
				creation <= '%(end_date)s'""" % args

		return query
	
	
	def get_bc_accounts_regex(self):
		"""
			Returns a regular expression of 'Bank or Cash' type account list
		"""
		bc_account_list = webnotes.conn.sql("""
			SELECT name
			FROM `tabAccount`
			WHERE account_type = 'Bank or Cash'""", as_list=1)
		
		return '(' + '|'.join([ac[0] for ac in bc_account_list]) + ')'
	

	def get(self):
		"""
			* Execute Query
			* Prepare Email Body from Print Format
		"""
		result, email_body = self.execute_queries()
		webnotes.msgprint(result)
		webnotes.msgprint(email_body)
		return result, email_body


	def execute_queries(self):
		"""
			* If standard==1, execute get_standard_data
			* If standard==0, execute python code in custom_code field
		"""
		result = {}
		if self.doc.use_standard==1:
			result = self.get_standard_data()
			email_body = self.get_standard_body(result)
		else:
			result, email_body = self.execute_custom_code(self.doc)

		#webnotes.msgprint(result)

		return result, email_body


	def get_standard_body(self, result):
		"""
			Generate email body depending on the result
		"""
		return """
			<div>
				Invoiced Amount: %(invoiced_amount)s<br />
				Payables: %(payables)s<br />
			</div>""" % result


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
		self.sending = True
		result, email_body = self.get()
		# TODO: before sending, check if user is disabled or not
		from webnotes.utils.email_lib import sendmail
		try:
			sendmail(
				recipients=self.doc.recipient_list.split("\n"),
				sender='anand@erpnext.com',
				reply_to='support@erpnext.com',
				subject='Digest',
				msg=email_body,
				from_defs=1
			)
		except Exception, e:
			webnotes.msgprint('There was a problem in sending your email. Please contact support@erpnext.com')
			#webnotes.errprint(webnotes.getTraceback())


	def on_update(self):
		"""

		"""
		import webnotes
		args = {
			'db_name': webnotes.conn.get_value('Control Panel', '', 'account_id'),
			'event': 'setup.doctype.email_digest.email_digest.send'
		}
		from webnotes.utils.scheduler import Scheduler
		sch = Scheduler()
		sch.connect()

		if self.doc.enabled == 1:
			# Create scheduler entry
			res = sch.conn.sql("""
				SELECT * FROM Event
				WHERE
					db_name = %(db_name)s AND
					event = %(event)s
			""", args)

			if not (res and res[0]):
				args['next_execution'] = self.get_next_execution()
				
				sch.conn.sql("""
					INSERT INTO	Event (db_name, event, `interval`, next_execution, recurring)
					VALUES (%(db_name)s, %(event)s, 86400, %(next_execution)s, 1)
				""", args)

		else:
			# delete scheduler entry
			sch.clear(args['db_name'], args['event'])
	

	def get_next_sending(self):
		"""

		"""
		# Get TimeZone
		# Get System TimeZone
		import time
		from pytz import timezone
		import datetime
		import webnotes.defs
		cp = webnotes.model.doc.Document('Control Panel','Control Panel')
		app_tz = timezone(cp.time_zone)
		server_tz = timezone(getattr(webnotes.defs, 'system_timezone'))
		
		start_date, end_date = self.get_start_end_dates()
		
		new_date = end_date + datetime.timedelta(days=1)
		new_time = datetime.time(hour=6)

		naive_dt = datetime.datetime.combine(new_date, new_time)
		app_dt = app_tz.localize(naive_dt)
		server_dt = server_tz.normalize(app_dt.astimezone(server_tz))

		res = {
			'app_dt': app_dt.replace(tzinfo=None),
			'app_tz': app_tz,
			'server_dt': server_dt.replace(tzinfo=None),
			'server_tz': server_tz
		}

		from webnotes.utils import formatdate
		str_date = formatdate(str(res['app_dt'].date()))
		str_time = res['app_dt'].time().strftime('%I:%M')

		self.doc.next_send = str_date + " at " + str_time

		return res


	def get_next_execution(self):
		"""

		"""
		from datetime import datetime, timedelta
		dt_args = self.get_next_sending()
		server_dt = dt_args['server_dt']
		now_dt = datetime.now(dt_args['server_tz'])
		if now_dt.time() <= server_dt.time():
			next_date = now_dt.date()
		else:
			next_date = now_dt.date() + timedelta(days=1)

		next_time = server_dt.time()

		return datetime.combine(next_date, next_time)


	def onload(self):
		"""

		"""
		self.get_next_sending()


def send():
	"""

	"""
	pass

