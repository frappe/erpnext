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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.model import db_exists
from webnotes.model.doc import addchild, make_autoname
from webnotes.model.bean import copy_doclist

sql = webnotes.conn.sql
	


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	# Autoname
	# ---------
	def autoname(self):
		self.doc.name = make_autoname(self.doc.naming_series+'.#####')


	def get_item_specification_details(self):
		self.doclist = self.doc.clear_table(self.doclist, 'qa_specification_details')
		specification = sql("select specification, value from `tabItem Quality Inspection Parameter` \
			where parent = '%s' order by idx" % (self.doc.item_code))
		for d in specification:
			child = addchild(self.doc, 'qa_specification_details', 'Quality Inspection Reading', self.doclist)
			child.specification = d[0]
			child.value = d[1]
			child.status = 'Accepted'

	def on_submit(self):
		if self.doc.purchase_receipt_no:
			sql("update `tabPurchase Receipt Item` t1, `tabPurchase Receipt` t2 set t1.qa_no = '%s', t2.modified = '%s' \
				where t1.parent = '%s' and t1.item_code = '%s' and t1.parent = t2.name" \
				% (self.doc.name, self.doc.modified, self.doc.purchase_receipt_no, self.doc.item_code))
		

	def on_cancel(self):
		if self.doc.purchase_receipt_no:
			sql("update `tabPurchase Receipt Item` t1, `tabPurchase Receipt` t2 set t1.qa_no = '', t2.modified = '%s' \
				where t1.parent = '%s' and t1.item_code = '%s' and t1.parent = t2.name" \
				% (self.doc.modified, self.doc.purchase_receipt_no, self.doc.item_code))
