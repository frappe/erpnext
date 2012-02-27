
def execute():
	import webnotes
	sql = webnotes.conn.sql
	from webnotes.model.code import get_obj
	
	# repost
	comp = sql("select name from tabCompany where docstatus!=2")
	fy = sql("select name from `tabFiscal Year` order by year_start_date asc")
	for c in comp:
		prev_fy = ''
		for f in fy:
			fy_obj = get_obj('Fiscal Year', f[0])
			fy_obj.doc.past_year = prev_fy
			fy_obj.doc.company = c[0]
			fy_obj.doc.save()

			fy_obj = get_obj('Fiscal Year', f[0])
			fy_obj.repost()
			prev_fy = f[0]
			sql("commit")
			sql("start transaction")
