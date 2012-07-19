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
	sql = webnotes.conn.sql
	
	# Reload item table
	reload_doc('accounts', 'doctype', 'pv_detail')
	reload_doc('buying', 'doctype', 'po_detail')
	reload_doc('stock', 'doctype', 'purchase_receipt_detail')
	
	# copy project value from parent to child
	sql("update `tabPurchase Order Item` t1, `tabPurchase Order` t2 set t1.project_name = t2.project_name where t1.parent = t2.name and ifnull(t1.project_name, '') = ''")
	sql("update `tabPurchase Invoice Item` t1, `tabPurchase Invoice` t2 set t1.project_name = t2.project_name where t1.parent = t2.name and ifnull(t1.project_name, '') = ''")
	sql("update `tabPurchase Receipt Item` t1, `tabPurchase Receipt` t2 set t1.project_name = t2.project_name where t1.parent = t2.name and ifnull(t1.project_name, '') = ''")
	
	# delete project from parent
	sql("delete from `tabDocField` where fieldname = 'project_name' and parent in ('Purchase Order', 'Purchase Receipt', 'Purchase Invoice')")

