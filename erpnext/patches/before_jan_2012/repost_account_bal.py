
def execute():
	import webnotes
	sql = webnotes.conn.sql
	from webnotes.model.code import get_obj
	
	# stop session
	webnotes.conn.set_global('__session_status', 'stop')
	webnotes.conn.set_global('__session_status_message', 'Patch is running in background. \nPlease wait until it completed...\n')
	
	webnotes.conn.commit()
	webnotes.conn.begin()
	
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
			fy_obj.repost()
			prev_fy = f[0]
			sql("commit")
			sql("start transaction")

	# free session
	webnotes.conn.set_global('__session_status', '')
	webnotes.conn.set_global('__session_status_message', '')
