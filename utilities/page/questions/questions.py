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

from __future__ import unicode_literals
import webnotes

from webnotes.utils import load_json
import json

@webnotes.whitelist()
def get_questions():
	"""get list of questions"""
	import json
	conds = ''
	
	if 'search_text' in webnotes.form_dict:
		conds = ' and t1.question like "%'+ webnotes.form_dict['search_text'] + '%"'
		
	if 'tag_filters' in webnotes.form_dict:
		tag_filters = json.loads(webnotes.form_dict['tag_filters'])
		for t in tag_filters:
			conds += ' and t1._user_tags like "%'+ t +'%"'
	
	return webnotes.conn.sql("""select t1.name, t1.owner, t1.question, t1.modified, t1._user_tags,
			(select count(*) from tabAnswer where
			tabAnswer.question = t1.name) as answers
		from tabQuestion t1, tabProfile t2
		where t1.docstatus!=2
		and t1.owner = t2.name
		%(conds)s
		order by t1.modified desc""" % {"conds":conds}, as_dict=1)

# add a new question
@webnotes.whitelist()
def add_question(arg):
	args = load_json(arg)
	
	from webnotes.model.doc import Document
	d = Document('Question')
	d.question = args['question']
	d.points = 1
	d.save(1)
	
	if args['suggest']:
		from core.page.messages import messages
		for s in args['suggest']:
			if s:
				messages.post(json.dumps({
					'contact': s,
					'txt': 'Please help me and answer the question "%s" in the Knowledge Base' % d.question,
					'notify': 1
				}))

@webnotes.whitelist()
def delete(arg):
	"""
		delete a question or answer (called from kb toolbar)
	"""
	args = load_json(arg)
	from webnotes.model import delete_doc
	delete_doc(args['dt'], args['dn'])
