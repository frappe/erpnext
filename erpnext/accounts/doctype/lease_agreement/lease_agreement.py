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
			Create Lease Id using naming_series pattern
		"""
		self.doc.name = make_autoname(self.doc.naming_series+ '.#####')

	def lease_installment_post(self, args):
		"""
			Posts the Installment receipt into Journal Voucher
		"""
		next_inst = sql("select amount,name from `tabLease Installment` where parent=%s and ifnull(cheque_number,'')='' order by due_date limit 1",self.doc.name)

		data = json.loads(args)
		data['voucher_type']='Lease Receipt'
		data['naming_series']='JV'
		data['amount']=next_inst[0][0]
		data['debit_account']=data.get('bank_account')
		data['credit_account']=self.doc.account
		data['fiscal_year']=get_defaults()['fiscal_year']
		data['company']=get_defaults()['company']
		jv_name=post_jv(data)

		sql("update `tabLease Installment` set cheque_number=%s, cheque_date=%s, jv_number=%s where name=%s",(data.get('cheque_number'),data.get('cheque_date'),jv_name,next_inst[0][1]))

		self.doclist = [Document(d.doctype, d.name) for d in self.doclist]
