import webnotes

def execute():
	# check for selling
	webnotes.conn.sql("""update `tabItem Price` set selling=1
		where ifnull(selling, 0)=0 and ifnull(buying, 0)=0""")
	