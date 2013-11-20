# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import webnotes
from webnotes import session, msgprint
from webnotes.utils import today

	

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def validate(self):
		if session['user'] != 'Guest' and not self.doc.customer:
			msgprint("Please select Customer from whom issue is raised",
				raise_exception=True)
				
		if self.doc.status=="Closed" and \
			webnotes.conn.get_value("Customer Issue", self.doc.name, "status")!="Closed":
			self.doc.resolution_date = today()
			self.doc.resolved_by = webnotes.session.user
	
	def on_cancel(self):
		lst = webnotes.conn.sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent = t1.name and t2.prevdoc_docname = '%s' and	t1.docstatus!=2"%(self.doc.name))
		if lst:
			lst1 = ','.join([x[0] for x in lst])
			msgprint("Maintenance Visit No. "+lst1+" already created against this customer issue. So can not be Cancelled")
			raise Exception
		else:
			webnotes.conn.set(self.doc, 'status', 'Cancelled')

	def on_update(self):
		pass

@webnotes.whitelist()
def make_maintenance_visit(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	visit = webnotes.conn.sql("""select t1.name 
		from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 
		where t2.parent=t1.name and t2.prevdoc_docname=%s 
		and t1.docstatus=1 and t1.completion_status='Fully Completed'""", source_name)
		
	if not visit:
		doclist = get_mapped_doclist("Customer Issue", source_name, {
			"Customer Issue": {
				"doctype": "Maintenance Visit", 
				"field_map": {
					"complaint": "description", 
					"doctype": "prevdoc_doctype", 
					"name": "prevdoc_docname"
				}
			}
		}, target_doclist)
	
		return [d.fields for d in doclist]