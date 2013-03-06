import webnotes

def execute():
	for cform in webnotes.conn.sql("""select name from `tabC-Form` where docstatus=2"""):
		webnotes.conn.sql("""update `tabSales Invoice` set c_form_no=null
			where c_form_no=%s""", cform[0])