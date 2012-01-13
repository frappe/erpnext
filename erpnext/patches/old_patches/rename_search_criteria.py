import webnotes
from webnotes.model.code import get_obj
def execute():
	for sc in webnotes.conn.sql("""select name from `tabSearch Criteria` where ifnull(name,'')
		like 'srch%' or ifnull(name,'') like '%stdsrch'"""):
		get_obj('Search Criteria', sc[0]).rename()
