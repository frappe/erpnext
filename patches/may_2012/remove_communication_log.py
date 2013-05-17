from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.reload_doc('support', 'doctype', 'communication')
	webnotes.conn.commit()
	webnotes.conn.begin()
	
	# change doctype property setter and custom fields, and save them
	move_customizations()
	
	try:
		remove_communication_log()
	except Exception, e:
		if e.args[0] != 1146:
			raise e

def move_customizations():
	import webnotes.model.doc
	import webnotes.model.doctype

	res = webnotes.conn.sql("""\
		delete from `tabProperty Setter`
		where property='previous_field'
		and doc_type = 'Communication Log'""")
	
	res = webnotes.conn.sql("""\
		select name from `tabCustom Field`
		where dt='Communication Log'""")
	for r in res:
		d = webnotes.model.doc.Document('Custom Field', r[0])
		d.dt = 'Communication'
		d.save()
	from webnotes.model.db_schema import updatedb
	updatedb('Communication')

	res = webnotes.conn.sql("""\
		select field_name from `tabProperty Setter`
		where doc_type='Communication Log' and field_name is not null""")
	
	doclist = webnotes.model.doctype.get('Communication', 0)
	field_list = [d.fieldname for d in doclist if d.doctype=='DocField']
	for r in res:
		if r[0] in field_list:
			webnotes.conn.sql("""\
				update `tabProperty Setter`
				set doc_type = 'Communication'
				where field_name=%s and doc_type='Communication Log'""", r[0])
				
	webnotes.conn.sql("""\
		delete from `tabProperty Setter`
		where doc_type='Communication Log'""")

	webnotes.clear_cache(doctype="Communication")

def remove_communication_log():
	import webnotes
	import webnotes.model
	import webnotes.model.doc
	import webnotes.model.doctype
	
	webnotes.conn.auto_commit_on_many_writes = True
	
	# get all communication log records
	comm_log_list = webnotes.conn.sql("select * from `tabCommunication Log`",
						as_dict=1)
	
	field_list = [d.fieldname for d in \
		webnotes.model.doctype.get('Communication', 0) \
		if d.doctype=='DocField']
	
	# copy it to communication
	for comm_log in comm_log_list:
		d = webnotes.model.doc.Document('Communication')
		
		for key in comm_log.keys():
			if key not in webnotes.model.default_fields:
				d.fields[key] = comm_log[key]
		
		parenttype = (comm_log.get('parenttype') or '').lower()
		if parenttype in field_list:
			d.fields[parenttype] = comm_log.get('parent')
		
		d.naming_series = 'COMM-'
		d.subject = 'Follow Up'
		d.content = comm_log.get('notes') or ''
		d.medium = comm_log.get('follow_up_type') or ''
		d.sales_person = comm_log.get('follow_up_by')
		d.communication_date = comm_log.get('date')
		d.category = 'Miscellaneous'
		d.action = 'No Action'
		d.save(ignore_fields=1)
	
	# delete records with parent type "Customer", "Lead", "Supplier"
	webnotes.conn.sql("""\
		delete from `tabCommunication Log`
		where parenttype in ('Customer', 'Lead', 'Supplier', 
			'Opportunity', 'Quotation')""")
	
	# if all records deleted, drop table communication log
	# and delete doctype communication log
	# if for some reason, records remain, dont drop table and dont delete doctype
	count = webnotes.conn.sql("select count(*) from `tabCommunication Log`")[0][0]
	if not count:
		webnotes.model.delete_doc('DocType', 'Communication Log')
		webnotes.conn.commit()
		webnotes.conn.sql("drop table `tabCommunication Log`")
		webnotes.conn.begin()