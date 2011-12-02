import webnotes

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc, self.doclist = doc, doclist	


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
				'field': 'debit',
				'type': 'Customer',
			}),

			'payables': self.generate_gle_query({
				'field': 'credit',
				'type': 'Supplier',
			}),

			'collections': self.generate_gle_query({
				'field': 'credit',
				'type': 'Customer',
				'against': 'Bank or Cash'
			}),

			'payments': self.generate_gle_query({
				'field': 'debit',
				'type': 'Supplier',
				'against': 'Bank or Cash'
			}),

			'income': self.generate_gle_query({
				'debit_or_credit': 'Credit'
			}),

			'expenses_booked': self.generate_gle_query({
				'debit_or_credit': 'Debit'
			}),

			'bank_balance': self.generate_gle_query({
				'bank_balance': None
			}),

			'new_leads': """""",

			'new_inquiries': """""",

			'new_quotations': "",

			'new_orders': "",

			'stock_below_rl': """""",

			'new_transactions': """"""

		}

		result = {}

		for query in query_dict.keys():
			if query_dict[query]:
				webnotes.msgprint(query)
				res = webnotes.conn.sql(query_dict[query], as_dict=1, debug=1)
				if query == 'income':
					res[0]['value'] = float(res[0]['credit'] - res[0]['debit'])
				elif query == 'expenses_booked':
					res[0]['value'] = float(res[0]['debit'] - res[0]['credit'])
				elif query == 'bank_balance':
					for r in res:
						r['value'] = float(r['debit'] - r['credit'])
				webnotes.msgprint(query)
				webnotes.msgprint(res)
				result[query] = (res and res[0]) and res[0] or None

		return result


	def generate_gle_query(self, args):
		"""
			Returns generated query string
		"""
		start_date = '2011-11-01'
		end_date = '2011-11-30'
		args.update({
			'start_date': start_date,
			'end_date': end_date,
			'company': self.doc.company,
			'select': None,
			'where': None
		})


		self.evaluate_query_conditions(args)
		
		query = """
			SELECT
				%(select)s,
				COUNT(*) AS 'count'
			FROM
				`tabGL Entry` gle,
				`tabAccount` ac
			WHERE
				gle.company = '%(company)s' AND
				gle.account = ac.name AND
				ac.docstatus < 2 AND
				IFNULL(gle.is_cancelled, 'No') = 'No' AND
				%(where)s AND
				gle.posting_date <= '%(end_date)s'""" % args

		if 'group_by' in args.keys():
			query = query + args['group_by']
		
		return query


	def evaluate_query_conditions(self, args):
		"""
			Modify query according to type of information required based on args passed 
		"""
		# If collections or payments
		if 'against' in args.keys():
			if args['against'] == 'Bank or Cash':
				bc_account_list = webnotes.conn.sql("""
					SELECT name
					FROM `tabAccount`
					WHERE account_type = 'Bank or Cash'""", as_list=1)
				args['reg'] = '(' + '|'.join([ac[0] for ac in bc_account_list]) + ')'
				args['where'] = """
					ac.master_type = '%(type)s' AND
					gle.against REGEXP '%(reg)s' AND
					gle.posting_date >= '%(start_date)s'""" % args
		
		# If income or expenses_booked
		elif 'debit_or_credit' in args.keys():
			args['select'] = """
				SUM(IFNULL(gle.debit, 0)) AS 'debit',
				SUM(IFNULL(gle.credit, 0)) AS 'credit'"""

			args['where'] = """
				ac.is_pl_account = 'Yes' AND
				ac.debit_or_credit = '%(debit_or_credit)s' AND
				gle.posting_date >= '%(start_date)s'""" % args

		elif 'bank_balance' in args.keys():
			args['select'] = "ac.name AS 'name', SUM(IFNULL(debit, 0)) AS 'debit', SUM(IFNULL(credit, 0)) AS 'credit'"
			args['where'] = "ac.account_type = 'Bank or Cash'"
			args['group_by'] = "GROUP BY ac.name"

		# For everything else
		else:
			args['where'] = """
				ac.master_type = '%(type)s' AND
				gle.posting_date >= '%(start_date)s'""" % args
	
		if not args['select']:
			args['select'] = "SUM(IFNULL(gle.%(field)s, 0)) AS '%(field)s'" % args


	def get(self):
		"""
			* Execute Query
			* Prepare Email Body from Print Format
		"""
		pass


	def execute_queries(self):
		"""
			* If standard==1, execute get_standard_data
			* If standard==0, execute python code in custom_code field
		"""
		pass


	def send(self):
		"""
			* Execute get method
			* Send email to recipients
		"""
		pass
