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
	sql = webnotes.conn.sql
	from webnotes.model.code import get_obj
	
	# repost
	comp = sql("select name from tabCompany where docstatus!=2")
	fy = sql("select name from `tabFiscal Year` order by year_start_date asc")
	for c in comp:
		prev_fy = ''
		for f in fy:
			fy_obj = get_obj('Fiscal Year', f[0])
			fy_obj.doc.past_year = prev_fy
			fy_obj.doc.company = c[0]
			fy_obj.doc.save()

			fy_obj = get_obj('Fiscal Year', f[0])
			fy_obj.repost()
			prev_fy = f[0]
			sql("commit")
			sql("start transaction")
