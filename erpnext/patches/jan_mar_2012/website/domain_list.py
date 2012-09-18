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
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	reload_doc('website', 'doctype', 'website_settings')

	res = webnotes.conn.sql("""\
		SELECT name FROM `tabDocPerm`
		WHERE parent='Website Settings' AND role='All' AND permlevel=1""")
	if not res:
		idx = webnotes.conn.sql("""\
			SELECT MAX(idx) FROM `tabDocPerm`
			WHERE parent='Website Settings'
			""")[0][0]
		from webnotes.model.doc import Document
		d = Document('DocType', 'Website Settings')
		perm = d.addchild('permissions', 'DocPerm')
		perm.read = 1
		perm.role = 'All'
		perm.permlevel = 1
		perm.idx = idx + 1
		perm.save()

