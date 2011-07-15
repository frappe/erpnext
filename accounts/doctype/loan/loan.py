import webnotes
from webnotes.model.doc import make_autoname, Document, addchild
from webnotes import msgprint
from webnotes.utils import get_defaults
import json
sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist):
		self.doc, self.doclist = doc, doclist
		
	def autoname(self):
		"""
			Create Loan Id using naming_series pattern
		"""
		self.doc.name = make_autoname(self.doc.naming_series+ '.#####')

	def loan_post(self, args):
		"""
			Posts the loan receipt into Journal Voucher
		"""
		data = json.loads(args)

		jv = Document('Journal Voucher')
		jv.voucher_type = 'Loan Receipt'
		jv.naming_series = 'JV'
		jv.voucher_date = data.get('cheque_date')
		jv.posting_date = data.get('cheque_date')
		jv.cheque_no = data.get('cheque_number')
		jv.cheque_date = data.get('cheque_date')
		jv.fiscal_year = get_defaults()['fiscal_year'] # To be modified to take care
		jv.company = get_defaults()['company']

		jv.save(1)

		next_inst = sql("select amount,name from `tabLoan Installment` where parent=%s and ifnull(cheque_number,'')='' order by due_date limit 1",self.doc.name)
		
		jc = addchild(jv,'entries','Journal Voucher Detail',0)
		jc.account = data.get('bank_account')
		jc.debit = next_inst[0][0]
		jc.save()

		jc = addchild(jv,'entries','Journal Voucher Detail',0)
		jc.account = self.doc.account
		jc.credit = next_inst[0][0]
		jc.save()

		sql("update `tabLoan Installment` set cheque_number=%s, cheque_date=%s, jv_number=%s where name=%s",(data.get('cheque_number'),data.get('cheque_date'),jv.name,next_inst[0][1]))

		self.doclist = [Document(d.doctype, d.name) for d in self.doclist]

