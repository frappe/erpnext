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
	opts = webnotes.conn.sql("""\
		SELECT options FROM `tabDocField`
		WHERE parent='Serial No' AND fieldname='status' AND
		fieldtype='Select'""")
	if opts and opts[0][0]:
		opt_list = opts[0][0].split("\n")
		if not "Purchase Returned" in opt_list:
			webnotes.conn.sql("""
				UPDATE `tabDocField` SET options=%s
				WHERE parent='Serial No' AND fieldname='status' AND
				fieldtype='Select'""", "\n".join(opt_list + ["Purchase Returned"]))
			webnotes.conn.commit()
			webnotes.conn.begin()

	from webnotes.modules import reload_doc
	reload_doc('stock', 'doctype', 'serial_no')
