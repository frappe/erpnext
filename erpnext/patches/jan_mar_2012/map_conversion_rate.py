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
from webnotes.model.code import get_obj
from webnotes.model.doc import addchild

def execute():
	"""
		* Maps conversion rate in doctype mapper PO-PR
		* Maps conversion rate in doctype mapper PO-PV
	"""
	args = [
		{
			'parent': 'Purchase Order-Purchase Receipt',
			'map': [{
				'from_table': 'Purchase Order',
				'to_table': 'Purchase Receipt',
				'fields': [['conversion_rate', 'conversion_rate', 'Yes']]
			}]
		},
		{
			'parent': 'Purchase Order-Purchase Invoice',
			'map': [{
				'from_table': 'Purchase Order',
				'to_table': 'Purchase Invoice',
				'fields': [['conversion_rate', 'conversion_rate', 'Yes']]
			}]
		},
	]

	for a in args:
		for m in a['map']:
			match_id = webnotes.conn.sql("""\
				SELECT match_id FROM `tabTable Mapper Detail`
				WHERE parent=%s AND from_table=%s AND to_table=%s\
				""", (a['parent'], m['from_table'], m['to_table']))[0][0]
			for f in m['fields']:
				res = webnotes.conn.sql("""\
					SELECT name FROM `tabField Mapper Detail`
					WHERE parent=%s AND from_field=%s AND to_field=%s
					AND match_id=%s""", (a['parent'], f[0], f[1], match_id))
				if not res:
					max_idx = webnotes.conn.sql("""\
						SELECT IFNULL(MAX(idx), 0) FROM `tabField Mapper Detail`
						WHERE parent=%s""", a['parent'])[0][0]
					obj = get_obj('DocType Mapper', a['parent'])
					c = addchild(obj.doc, 'field_mapper_details', 'Field Mapper Detail', obj.doclist)
					c.from_field = f[0]
					c.to_field = f[1]
					c.fields['map'] = f[2]
					c.match_id = match_id
					c.idx = max_idx + 1
					c.save()
