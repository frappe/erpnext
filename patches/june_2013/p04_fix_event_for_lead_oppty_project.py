import webnotes

def execute():
	from utilities.transaction_base import delete_events
	
	# delete orphaned Event User
	webnotes.conn.sql("""delete from `tabEvent User`
		where not exists(select name from `tabEvent` where `tabEvent`.name = `tabEvent User`.parent)""")
		
	for dt in ["Lead", "Opportunity", "Project"]:
		for ref_name in webnotes.conn.sql_list("""select ref_name 
			from `tabEvent` where ref_type=%s and ifnull(starts_on, '')='' """, dt):
				if webnotes.conn.exists(dt, ref_name):
					if dt in ["Lead", "Opportunity"]:
						webnotes.get_obj(dt, ref_name).add_calendar_event(force=True)
					else:
						webnotes.get_obj(dt, ref_name).add_calendar_event()
				else:
					# remove events where ref doc doesn't exist
					delete_events(dt, ref_name)