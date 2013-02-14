from __future__ import unicode_literals

import webnotes

@webnotes.whitelist()
def get_events(start, end):
	roles = webnotes.get_roles()
	events = webnotes.conn.sql("""select name as `id`, subject as title, 
		starts_on as `start`, ends_on as `end`, "Event" as doctype, owner 
		from tabEvent where event_date between %s and %s 
		and (event_type='Public' or owner=%s
		or exists(select * from `tabEvent User` where 
			`tabEvent User`.parent=tabEvent.name and person=%s)
		or exists(select * from `tabEvent Role` where 
			`tabEvent Role`.parent=tabEvent.name 
			and `tabEvent Role`.role in ('%s')))""" % ('%s', '%s', '%s', '%s',
			"', '".join(roles)), (start, end, 
			webnotes.session.user, webnotes.session.user), as_dict=1, debug=1)
	
	return events
			
	block_days = webnotes.conn.sql("""select block_date as `start`,
		name as `id`, reason as `title`, "Holiday List Block Date" as doctype,
		where block_date between %s and %s
		and """)
			
@webnotes.whitelist()
def update_event(name, start, end):
	webnotes.conn.sql("""update tabEvent set starts_on=%s, ends_on=%s where 
		name=%s""", (start, end, name))
	