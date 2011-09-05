import webnotes
from webnotes.utils import add_days, cint, cstr, flt, getdate
from webnotes.model.doclist import getlist
from webnotes.model.code import get_obj
from webnotes import session, form, is_testing, msgprint, errprint

sql = webnotes.conn.sql
get_value = webnotes.conn.get_value

#---------------------------------------------------------------------

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	# Get fiscal year based on date
	def get_year(self, dt):
		yr = sql("select name from `tabFiscal Year` where %s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day)",dt)
		return yr and yr[0][0] or ''

	# Get gl entries for the period and account
	def get_gl_entries(self, lft, rgt):
		gle = sql("select t1.posting_date, t1.voucher_type, t1.voucher_no, t1.debit, t1.credit, t1.remarks from `tabGL Entry` t1, `tabAccount` t2 WHERE t1.posting_date >= %s AND t1.posting_date <= %s and ifnull(t1.is_opening, 'No') = 'No' AND t1.account = t2.name AND t2.lft >= %s AND t2.rgt <= %s and ifnull(t1.is_cancelled, 'No') = 'No'", (self.doc.from_date, self.doc.to_date, lft, rgt), as_dict=1)
		entries, dr, cr = [], 0, 0
		for d in gle:
			dr, cr = dr + flt(d['debit']), cr + flt(d['credit'])
			entries.append(['', d['posting_date'], d['voucher_type'], d['voucher_no'], d['debit'], d['credit'], d['remarks']])
		return entries, dr, cr

	# Get Report Data
	def get_report_data(self):
		from_date_year = self.get_year(add_days(self.doc.from_date, -1))
		to_date_year = self.get_year(self.doc.to_date)

		# result initiatlization
		header = 'Ledger Balances Between ' + getdate(self.doc.from_date).strftime('%d-%m-%Y') + ' and ' + getdate(self.doc.to_date).strftime('%d-%m-%Y')
		res = [[header], ['Account', 'Posting Date', 'Voucher Type', 'Voucher No', 'Debit', 'Credit', 'Remarks']]
		glc = get_obj('GL Control')

		for d in getlist(self.doclist, 'ledger_details'):
			# Fetch acc details
			acc_det = sql("select debit_or_credit, is_pl_account, lft, rgt from tabAccount where name = '%s'" % d.account, as_dict=1)[0]

			# Opening
			opening = glc.get_as_on_balance(d.account, from_date_year, add_days(self.doc.from_date, -1), acc_det['debit_or_credit'], acc_det['lft'], acc_det['rgt'])[2]
			if acc_det['debit_or_credit'] == 'Credit':
				opening = -1*opening

			# GL Entries
			gle, debit, credit = self.get_gl_entries(acc_det['lft'], acc_det['rgt'])

			# Closing
			closing = opening + debit - credit

			# Append to result
			res.append([d.account])
			res += gle
			res.append(['', '', '', 'Total Debit/Credit', debit, credit])
			res.append(['', '', '', 'Opening Balance', opening])
			res.append(['', '', '', 'Closing Balance', closing])

		return res
