import webnotes

def execute():
	webnotes.reload_doc("stock", "doctype", "item_price")
	
	# check for selling
	webnotes.conn.sql("""update `tabItem Price` set selling=1
		where ifnull(selling, 0)=0 and ifnull(buying, 0)=0""")
	