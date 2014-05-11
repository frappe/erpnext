import webnotes

def get_context():
	return {
		"partners": webnotes.conn.sql("""select * from `tabSales Partner`
			where show_in_website=1 order by name asc""", as_dict=True),
	}