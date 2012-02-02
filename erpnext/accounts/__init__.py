import webnotes

def get_default_bank_account():
	"""
		Get default bank account for a company
	"""
	company = webnotes.form_dict.get('company')
	if not company: return
	res = webnotes.conn.sql("""\
		SELECT default_bank_account FROM `tabCompany`
		WHERE name=%s AND docstatus<2""", company)
	
	if res: return res[0][0]
