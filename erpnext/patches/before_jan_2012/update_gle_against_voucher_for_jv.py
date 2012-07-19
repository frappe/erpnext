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
	from webnotes.model.code import get_obj
	
	# select jv where against_jv exists
	jv = webnotes.conn.sql("select distinct parent from `tabJournal Voucher Detail` where docstatus = 1 and ifnull(against_jv, '') != ''")

	for d in jv:
		jv_obj = get_obj('Journal Voucher', d[0], with_children=1)

		# cancel
		get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =1, adv_adj = 1)

		#re-submit
		get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =0, adv_adj = 1)
