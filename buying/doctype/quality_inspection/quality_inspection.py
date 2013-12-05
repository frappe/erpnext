# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.model.doc import addchild

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def get_item_specification_details(self):
		self.doclist = self.doc.clear_table(self.doclist, 'qa_specification_details')
		specification = webnotes.conn.sql("select specification, value from `tabItem Quality Inspection Parameter` \
			where parent = '%s' order by idx" % (self.doc.item_code))
		for d in specification:
			child = addchild(self.doc, 'qa_specification_details', 'Quality Inspection Reading', self.doclist)
			child.specification = d[0]
			child.value = d[1]
			child.status = 'Accepted'

	def on_submit(self):
		if self.doc.purchase_receipt_no:
			webnotes.conn.sql("update `tabPurchase Receipt Item` t1, `tabPurchase Receipt` t2 set t1.qa_no = '%s', t2.modified = '%s' \
				where t1.parent = '%s' and t1.item_code = '%s' and t1.parent = t2.name" \
				% (self.doc.name, self.doc.modified, self.doc.purchase_receipt_no, self.doc.item_code))
		

	def on_cancel(self):
		if self.doc.purchase_receipt_no:
			webnotes.conn.sql("update `tabPurchase Receipt Item` t1, `tabPurchase Receipt` t2 set t1.qa_no = '', t2.modified = '%s' \
				where t1.parent = '%s' and t1.item_code = '%s' and t1.parent = t2.name" \
				% (self.doc.modified, self.doc.purchase_receipt_no, self.doc.item_code))


def item_query(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("from"):
		from webnotes.widgets.reportview import get_match_cond
		filters.update({
			"txt": txt,
			"mcond": get_match_cond(filters["from"], searchfield),
			"start": start,
			"page_len": page_len
		})
		return webnotes.conn.sql("""select item_code from `tab%(from)s` 
			where parent='%(parent)s' and docstatus < 2 and item_code like '%%%(txt)s%%' %(mcond)s
			order by item_code limit %(start)s, %(page_len)s""" % filters)