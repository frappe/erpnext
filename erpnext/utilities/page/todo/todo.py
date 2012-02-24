import webnotes
from webnotes.model.doc import Document

@webnotes.whitelist()
def get(arg=None):
	"""get todo list"""
	return webnotes.conn.sql("""select name, owner, description, date,
		priority, checked, reference_type, reference_name, assigned_by
		from `tabToDo Item` where owner=%s 
		order by field(priority, 'High', 'Medium', 'Low') asc, date asc""",
		webnotes.session['user'], as_dict=1)

@webnotes.whitelist()		
def edit(arg=None):
	args = webnotes.form_dict

	d = Document('ToDo Item', args.get('name') or None)
	d.description = args['description']
	d.date = args['date']
	d.priority = args['priority']
	d.checked = args.get('checked', 0)
	d.owner = webnotes.session['user']
	d.save(not args.get('name') and 1 or 0)

	if args.get('name') and d.checked:
		notify_assignment(d)

	return d.name

@webnotes.whitelist()
def delete(arg=None):
	name = webnotes.form_dict['name']
	d = Document('ToDo Item', name)
	if d and d.name:
		notify_assignment(d)
	webnotes.conn.sql("delete from `tabToDo Item` where name = %s", name)

def notify_assignment(d):
	doc_type = d.reference_type
	doc_name = d.reference_name
	assigned_by = d.assigned_by
	
	if doc_type and doc_name and assigned_by:
		from webnotes.widgets.form import assign_to
		assign_to.notify_assignment(assigned_by, d.owner, doc_type, doc_name)
		