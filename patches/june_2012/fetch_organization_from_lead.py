from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.conn.sql("update `tabQuotation` t1, `tabLead` t2 set t1.organization = t2.company_name where ifnull(t1.lead, '') != ''  and t1.quotation_to = 'Lead' and ifnull(t1.organization, '') = '' and t1.lead = t2.name")