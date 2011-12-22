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
			if self.doc.fields[query] and query_dict[query]:
				#webnotes.msgprint(query)
				res = webnotes.conn.sql(query_dict[query], as_dict=1)
				if query == 'income':
					for r in res:
						r['value'] = float(r['credit'] - r['debit'])
				elif query in ['expenses_booked', 'bank_balance']:
					for r in res:
						r['value'] = float(r['debit'] - r['credit'])
				#webnotes.msgprint(query)
				#webnotes.msgprint(res)
				result[query] = (res and len(res)==1) and res[0] or (res and res or None)
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
		#print "before scheduler"
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
		#print "after on update"
	

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

		self.doc.next_send = str_date + " at about " + str_time

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


	def get_standard_body(self, result):
		"""
			Generate email body depending on the result
		"""
		from webnotes.utils import fmt_money
		from webnotes.model.doc import Document
		company = Document('Company', self.doc.company)
		currency = company.default_currency

		def table(args):
			if type(args['body']) == type(''):
				table_body = """\
					<tbody><tr>
						<td style='padding: 5px; font-size: 24px; \
						font-weight: bold; background: #F7F7F5'>""" + \
					args['body'] + \
					"""\
						</td>
					</tr></tbody>"""

			elif type(args['body'] == type([])):
				body_rows = []
				for rows in args['body']:
					for r in rows:
						body_rows.append("""\
							<tr>
								<td style='padding: 5px; font-size: 24px; \
								font-weight: bold; background: #F7F7F5'>""" \
								+ r + """\
								</td>
							</tr>""")

					body_rows.append("<tr><td style='background: #F7F7F5'><br></td></tr>")

				table_body = "<tbody>" + "".join(body_rows) + "</tbody>"

			table_head = """\
				<thead><tr>
					<td style='padding: 5px; background: #D8D8D4; font-size: 16px; font-weight: bold'>""" \
					+ args['head'] + """\
					</td>
				</tr></thead>"""

			return "<table style='border-collapse: collapse; width: 100%;'>" \
				+ table_head \
				+ table_body \
				+ "</table>"

		currency_amount_str = "<span style='color: grey; font-size: 12px'>%s</span> %s"

		body_dict = {

			'invoiced_amount': {
				'table': 'invoiced_amount' in result and table({
					'head': 'Invoiced Amount',
					'body': currency_amount_str \
						% (currency, fmt_money(result['invoiced_amount']['debit']))
				}),
				'idx': 300
			},

			'payables': {
				'table': 'payables' in result and table({
					'head': 'Payables',
					'body': currency_amount_str \
						% (currency, fmt_money(result['payables']['credit']))
				}),
				'idx': 200
			},

			'collections': {
				'table': 'collections' in result and table({
					'head': 'Collections',
					'body': currency_amount_str \
						% (currency, fmt_money(result['collections']['credit']))
				}),
				'idx': 301
			},

			'payments': {
				'table': 'payments' in result and table({
					'head': 'Payments',
					'body': currency_amount_str \
						% (currency, fmt_money(result['payments']['debit']))
				}),
				'idx': 201
			},

			'income': {
				'table': 'income' in result and table({
					'head': 'Income',
					'body': currency_amount_str \
						% (currency, fmt_money(result['income']['value']))
				}),
				'idx': 302
			},

			'expenses_booked': {
				'table': 'expenses_booked' in result and table({
					'head': 'Expenses Booked',
					'body': currency_amount_str \
						% (currency, fmt_money(result['expenses_booked']['value']))
				}),
				'idx': 202
			},

			'bank_balance': {
				'table': 'bank_balance' in result and result['bank_balance'] and table({
					'head': 'Bank Balance',
					'body': [
						[
							"<span style='font-size: 16px; font-weight: normal'>%s</span>" % bank['name'],
							currency_amount_str % (currency, fmt_money(bank['value']))
						] for bank in result['bank_balance']
					]
				}),
				'idx': 400
			},

			'new_leads': {
				'table': 'new_leads' in result and table({
					'head': 'New Leads',
					'body': '%s' % result['new_leads']['count']
				}),
				'idx': 100
			},

			'new_enquiries': {
				'table': 'new_enquiries' in result and table({
					'head': 'New Enquiries',
					'body': '%s' % result['new_enquiries']['count']
				}),
				'idx': 101
			},

			'new_quotations': {
				'table': 'new_quotations' in result and table({
					'head': 'New Quotations',
					'body': '%s' % result['new_quotations']['count']
				}),
				'idx': 102
			},

			'new_sales_orders': {
				'table': 'new_sales_orders' in result and table({
					'head': 'New Sales Orders',
					'body': '%s' % result['new_sales_orders']['count']
				}),
				'idx': 103
			},

			'new_purchase_orders': {
				'table': 'new_purchase_orders' in result and table({
					'head': 'New Purchase Orders',
					'body': '%s' % result['new_purchase_orders']['count']
				}),
				'idx': 104
			},

			'new_transactions': {
				'table': 'new_transactions' in result and table({
					'head': 'New Transactions',
					'body': '%s' % result['new_transactions']['count']
				}),
				'idx': 105
			}

			#'stock_below_rl': 
		}

		table_list = []

		# Sort these keys depending on idx value
		bd_keys = sorted(body_dict, key=lambda x: body_dict[x]['idx'])

		for k in bd_keys:
			if self.doc.fields[k]:
				if k in result:
					table_list.append(body_dict[k]['table'])
				elif k in ['collections', 'payments']:
					table_list.append(\
						"<div style='font-size: 16px; color: grey'>[" + \
							k.capitalize() + \
							"]<br />Missing: Account of type 'Bank or Cash'\
						</div>")
				elif k=='bank_balance':
					table_list.append(\
						"<div style='font-size: 16px; color: grey'>[" + \
							"Bank Balance" + \
							"]<br />Alert: GL Entry not found for Account of type 'Bank or Cash'\
						</div>")
					
		
		i = 0
		result = []
		op_len = len(table_list)
		while(True):
			if i>=op_len:
				break
			elif (op_len - i) == 1:
				result.append("""\
					<tr>
						<td style='width: 50%%; vertical-align: top;'>%s</td>
						<td></td>
					</tr>""" % (table_list[i]))
			else:
				result.append("""\
					<tr>
						<td style='width: 50%%; vertical-align: top;'>%s</td>
						<td>%s</td>
					</tr>""" % (table_list[i], table_list[i+1]))
			
			i = i + 2

		from webnotes.utils import formatdate
		start_date, end_date = self.get_start_end_dates()
		digest_daterange = self.doc.frequency=='Daily' \
			and formatdate(str(start_date)) \
			or (formatdate(str(start_date)) + " to " + (formatdate(str(end_date))))

		email_body = """
			<div style='width: 100%%'>
				<div style='padding: 10px; margin: auto; text-align: center; line-height: 80%%'>
					<p style='font-weight: bold; font-size: 24px'>%s</p>
					<p style='font-size: 16px; color: grey'>%s</p>
					<p style='font-size: 20px; font-weight: bold'>%s</p>
				</div>
				<table cellspacing=15 style='width: 100%%'>""" \
					% ((self.doc.frequency + " Digest"), \
						digest_daterange, self.doc.company) \
				+ "".join(result) + """\
				</table><br><p></p>
			</div>"""

		return email_body


def send():
	"""

	"""
	edigest_list = webnotes.conn.sql("""
		SELECT name FROM `tabEmail Digest`
		WHERE enabled=1
	""", as_list=1)

	from webnotes.model.code import get_obj
	from datetime import datetime, timedelta
	now = datetime.now()
	now_date = now.date()
	now_time = (now + timedelta(hours=2)).time()

	for ed in edigest_list:
		if ed[0]:
			ed_obj = get_obj('Email Digest', ed[0])
			ed_obj.sending = True
			dt_dict = ed_obj.get_next_sending()
			send_date = dt_dict['server_dt'].date()
			send_time = dt_dict['server_dt'].time()

			if (now_date == send_date) and (send_time <= now_time):
				#webnotes.msgprint('sending ' + ed_obj.doc.name)
				ed_obj.send()
			#else:
			#	webnotes.msgprint('not sending ' + ed_obj.doc.name)
