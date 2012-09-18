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

# Please edit this list and import only required elements
from __future__ import unicode_literals
import webnotes

from webnotes.utils import validate_email_add, cint, cstr
from webnotes.model.doc import Document
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql

# -----------------------------------------------------------------------------------------
# Notification control
class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

	# get message to load in custom text
	# ----------------------------------
	def get_message(self, arg):
		fn = arg.lower().replace(' ', '_') + '_message'
		v = sql("select value from tabSingles where field=%s and doctype=%s", (fn, 'Notification Control'))
		return v and v[0][0] or ''

	# set custom text
	# ---------------
	def set_message(self, arg = ''):
		fn = self.doc.select_transaction.lower().replace(' ', '_') + '_message'
		webnotes.conn.set(self.doc, fn, self.doc.custom_message)
		msgprint("Custom Message for %s updated!" % self.doc.select_transaction)

	
	def get_formatted_message(self, args):
		"""
			args can contain:
				* type
				* doctype
				* contact_name
		"""
		import json
		args = json.loads(args)
		res = {
			'send': 0,
			'message': self.prepare_message(args),
			'print_format': self.get_default_print_format(args)
		}

		dt_small = args.get('doctype').replace(' ', '_').lower()
		if cint(self.doc.fields.get(dt_small)):
			res['send'] = 1

		return json.dumps(res)


	def prepare_message(self, args):
		"""
			Prepares message body
		"""
		if args.get('type'):
			msg_dict = {}
			msg_dict['message'] = args.get('message') or self.get_message(args.get('type'))
			msg_dict['company'] = Document('Control Panel', 'Control Panel').company_name
			msg_dict['salutation'] = "Hi" + (args.get('contact_name') and (" " + args.get('contact_name')) or "")
			msg_dict['send_from'] = webnotes.conn.sql("""\
				SELECT CONCAT_WS(' ', first_name, last_name)
				FROM `tabProfile`
				WHERE name = %s""", webnotes.session['user'], as_list=1)[0][0] or ''
			
			return """\
				<div>
					%(salutation)s,

					%(message)s
					
					Thanks,
					%(send_from)s
					%(company)s
				</div>""" % msg_dict

		else: return ""


	def get_default_print_format(self, args):
		"""
			Get default print format from doclayer
		"""
		doclayer = get_obj('Customize Form', 'Customize Form')
		doclayer.doc.doc_type = args.get('doctype')
		doclayer.get()
		if doclayer.doc.default_print_format:
			return doclayer.doc.default_print_format
		else: return 'Standard'
