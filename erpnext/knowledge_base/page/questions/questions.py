# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import webnotes

from webnotes.utils import load_json, cint, cstr

# add a new question
@webnotes.whitelist()
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
	
@webnotes.whitelist()
def vote(arg):
	args = load_json(arg)
	
	res = webnotes.conn.sql("select points, _users_voted from `tab%s` where name=%s" % (args['dt'], '%s'), args['dn'])[0]
	p = cint(res[0])
	p = args['vote']=='up' and p+1 or p-1
	
	# update
	webnotes.conn.sql("update `tab%s` set points=%s, _users_voted=%s where name=%s" % (args['dt'], '%s', '%s', '%s'), \
		(p, cstr(res[1]) + ',' + webnotes.user.name, args['dn']))
	
	return p

@webnotes.whitelist()
def delete(arg):
	"""
		delete a question or answer (called from kb toolbar)
	"""
	args = load_json(arg)
	from webnotes.model import delete_doc
	delete_doc(args['dt'], args['dn'])