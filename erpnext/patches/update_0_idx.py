import webnotes
def execute():
	doc_type_list = webnotes.conn.sql("""SELECT DISTINCT parent FROM `tabDocField` where idx=0""")
	for doc_type in doc_type_list:
		if doc_type and doc_type[0]:
			webnotes.conn.sql("""\
				UPDATE `tabDocField` SET idx=idx+1
				WHERE parent=%s
			""", doc_type[0])
