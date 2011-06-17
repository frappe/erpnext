import webnotes

from webnotes.utils import load_json, cint, cstr

# add a new question
def add_question(arg):
	args = load_json(arg)
	
	from webnotes.model.doc import Document
	d = Document('Question')
	d.question = args['question'].title()
	d.points = 1
	d.save(1)
	
	if args['suggest']:
		from home.page.my_company.my_company import post_comment
		for s in args['suggest']:
			if s:
				post_comment({
					'uid': s,
					'comment': 'Please help me and answer the question "%s" in the Knowledge Base' % d.question,
					'notify': 1
				})
	
	
def vote(arg):
	args = load_json(arg)
	
	res = webnotes.conn.sql("select points, _users_voted from `tab%s` where name=%s" % (args['dt'], '%s'), args['dn'])[0]
	p = cint(res[0])
	p = args['vote']=='up' and p+1 or p-1
	
	# update
	webnotes.conn.sql("update `tab%s` set points=%s, _users_voted=%s where name=%s" % (args['dt'], '%s', '%s', '%s'), \
		(p, cstr(res[1]) + ',' + webnotes.user.name, args['dn']))
	
	return p
