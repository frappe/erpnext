import webnotes
from webnotes.utils import cint

def execute():
	import patches.september_2012.repost_stock
	patches.september_2012.repost_stock.execute()
	
	import patches.march_2013.p08_create_aii_accounts
	patches.march_2013.p08_create_aii_accounts.execute()
	
	copy_perpetual_accounting_settings()
	set_missing_cost_center()
	

def set_missing_cost_center():
	reload_docs = [
		["stock", "doctype", "serial_no"], 
		["stock", "doctype", "stock_reconciliation"],
		["stock", "doctype", "stock_entry"]
	]
	for d in reload_docs:
		webnotes.reload_doc(d[0], d[1], d[2])
	
	if cint(webnotes.defaults.get_global_default("perpetual_accounting")):
		for dt in ["Serial No", "Stock Reconciliation", "Stock Entry"]:
			webnotes.conn.sql("""update `tab%s` t1, tabCompany t2 
				set t1.cost_center=t2.cost_center where t1.company = t2.name""" % dt)
		
def copy_perpetual_accounting_settings():
	webnotes.reload_doc("accounts", "doctype", "accounts_settings")
	aii_enabled = cint(webnotes.conn.get_value("Global Defaults", None, 
		"auto_inventory_accounting"))
	if aii_enabled:
		try:
			bean= webnotes.bean("Account Settings")
			bean.doc.perpetual_accounting = aii_enabled
			bean.save()
		except:
			pass