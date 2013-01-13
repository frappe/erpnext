import webnotes
def execute():
	webnotes.conn.sql("""update tabDocPerm set `report`=`read`
		where ifnull(permlevel,0)=0""")
