from webnotes.model.doc import make_autoname, Document, addchild
# Posts JV

def post_jv(data):
	jv = Document('Journal Voucher')
	jv.voucher_type = data.get('voucher_type')
	jv.naming_series = data.get('naming_series')
	jv.voucher_date = data.get('cheque_date')
	jv.posting_date = data.get('cheque_date')
	jv.cheque_no = data.get('cheque_number')
	jv.cheque_date = data.get('cheque_date')
	jv.fiscal_year = data.get('fiscal_year') # To be modified to take care
	jv.company = data.get('company')

	jv.save(1)

	jc = addchild(jv,'entries','Journal Voucher Detail',0)
	jc.account = data.get('debit_account')
	jc.debit = data.get('amount')
	jc.save()

	jc = addchild(jv,'entries','Journal Voucher Detail',0)
	jc.account = data.get('credit_account')
	jc.credit = data.get('amount')
	jc.save()

	return jv.name