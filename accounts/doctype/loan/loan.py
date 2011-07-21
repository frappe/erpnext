import webnotes
from webnotes.model.doc import make_autoname, Document, addchild
from webnotes import msgprint
from webnotes.utils import get_defaults
import json
from accounts.utils import post_jv
sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist):
		self.doc, self.doclist = doc, doclist

	def autoname(self):
		"""
			Create Loan Id using naming_series pattern
		"""
		self.doc.name = make_autoname(self.doc.naming_series+ '.#####')

	def loan_post(self):
		data['voucher_type']='Loan Issue'
		data['naming_series']='JV'
		data['fiscal_year'] = get_defaults()['fiscal_year'] # To be modified to take care
		data['company'] = get_defaults()['company']
		data['debit_account'] = self.doc['receivable_account']
		data['credit_account'] = self.doc['account']
		data['amount'] = self.doc.loan_amount
		jv_name=post_jv(data)

	def loan_installment_post(self, args):
		"""
			Posts the loan receipt into Journal Voucher
		"""
		next_inst = sql("select amount,name from `tabLoan Installment` where parent=%s and ifnull(cheque_number,'')='' order by due_date limit 1",self.doc.name)

		data = json.loads(args)
		data['voucher_type']='Loan Receipt'
		data['naming_series']='JV'
		data['amount']=next_inst[0][0]
		data['debit_account']=data.get('bank_account')
		data['credit_account']=self.doc.account
		data['fiscal_year']=get_defaults()['fiscal_year']
		data['company']=get_defaults()['company']
		jv_name=post_jv(data)

		sql("update `tabLoan Installment` set cheque_number=%s, cheque_date=%s, jv_number=%s where name=%s",(data.get('cheque_number'),data.get('cheque_date'),jv_name,next_inst[0][1]))

		self.doclist = [Document(d.doctype, d.name) for d in self.doclist]

