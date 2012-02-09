import webnotes

def execute():
	from webnotes.model import delete_doc
	from webnotes.modules import reload_doc
	delete_doc("DocType", "SSO Control")
	delete_doc("DocType", "WN ERP Client Control")
	delete_doc("DocType", "Production Tips Common")
	delete_doc("DocType", "DocTrigger")
	delete_doc("Page", "Setup Wizard")
	
	# cleanup control panel
	delete_doc("DocType", "Control Panel")
	reload_doc("core", "doctype", "control_panel")
	
	webnotes.conn.sql("""delete from tabSingles
		where field like 'startup_%' and doctype='Control Panel'""")
	webnotes.conn.sql("""delete from __SessionCache""")

	webnotes.conn.commit()

	# DDLs
	# -------------------
	
	webnotes.conn.sql("drop table if exists tabDocTrigger")	

	try: webnotes.conn.sql("""alter table `tabFile Data` drop column blob_content""")
	except: pass
		
	webnotes.conn.sql("""alter table __PatchLog engine=InnoDB""")
	
