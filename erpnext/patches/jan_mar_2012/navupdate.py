import webnotes

def execute():
	from webnotes.modules import reload_doc
	reload_doc('accounts', 'page', 'accounts_home')
	reload_doc('selling', 'page', 'selling_home')
	reload_doc('buying', 'page', 'buying_home')
	reload_doc('stock', 'page', 'stock_home')
	reload_doc('hr', 'page', 'hr_home')
	reload_doc('support', 'page', 'support_home')
	reload_doc('production', 'page', 'production_home')
	reload_doc('projects', 'page', 'projects_home')
	reload_doc('website', 'page', 'website_home')
	
	webnotes.conn.commit()
	webnotes.conn.sql("""create table __SchedulerLog (
		`timestamp` timestamp,
		method varchar(200),
		error text
	) engine=MyISAM""")