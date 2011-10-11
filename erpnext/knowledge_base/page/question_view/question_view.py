import webnotes
from webnotes.utils import load_json, cstr, now

# update the editable text item
def update_item(args):
	args = load_json(args)
	
	webnotes.conn.sql("update `tab%s` set `%s`=%s, modified=%s where name=%s" \
		% (args['dt'], args['fn'], '%s', '%s', '%s'), (args['text'], now(), args['dn']))
		
def has_answered(arg):
	return webnotes.conn.sql("select name from tabAnswer where owner=%s and question=%s", (webnotes.user.name, arg)) and 'Yes' or 'No'

def get_question(arg):
	return cstr(webnotes.conn.sql("select question from tabQuestion where name=%s", arg)[0][0])

def add_answer(args):
	args = load_json(args)
	
	from webnotes.model.doc import Document
	
	a = Document('Answer')
	a.answer = args['answer']
	a.question = args['qid']
	a.points = 1
	a.save(1)
	
	webnotes.conn.set_value('Question', args['qid'], 'modified', now())