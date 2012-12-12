import webnotes, json

def execute():
	for p in webnotes.conn.sql("""select name, recent_documents from 
		tabProfile where ifnull(recent_documents,'')!=''"""):
		if not '~~~' in p[1]:
			webnotes.cache().set_value("recent:" + p[0], json.loads(p[1]))