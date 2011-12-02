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
		self.process_args(args)

		query = None

		if args['type'] in ['invoiced_amount', 'payables']:
			query = """
				SELECT
					SUM(IFNULL(gle.%(field)s, 0)) AS '%(field)s',
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
					SUM(IFNULL(gle.%(field)s, 0)) AS '%(field)s',
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
					SUM(IFNULL(gle.debit, 0)) AS 'debit',
					SUM(IFNULL(gle.credit, 0)) AS 'credit',
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
					SUM(IFNULL(gle.debit, 0)) AS 'debit',
					SUM(IFNULL(gle.credit, 0)) AS 'credit',
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
		start_date = '2011-11-01'
		end_date = '2011-11-30'

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
