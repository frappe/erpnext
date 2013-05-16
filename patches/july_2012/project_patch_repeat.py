from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("""update `tabPurchase Order Item` t1, `tabPurchase Order` t2
		set t1.project_name = t2.project_name where t1.parent = t2.name
		and ifnull(t1.project_name, '') = ''""")
	webnotes.conn.sql("""update `tabPurchase Invoice Item` t1, `tabPurchase Invoice` t2
		set t1.project_name = t2.project_name where t1.parent = t2.name
		and ifnull(t1.project_name, '') = ''""")
	webnotes.conn.sql("""update `tabPurchase Receipt Item` t1, `tabPurchase Receipt` t2
		set t1.project_name = t2.project_name where t1.parent = t2.name
		and ifnull(t1.project_name, '') = ''""")
	
	webnotes.conn.commit()
	webnotes.reload_doc("buying", "doctype", "purchase_order")
	webnotes.reload_doc("accounts", "doctype", "purchase_invoice")
	webnotes.conn.begin()