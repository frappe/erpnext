# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		for key in ["cust_master_name", "customer_group", "territory", "maintain_same_sales_rate",
			"editable_price_list_rate"]:
				webnotes.conn.set_default(key, self.doc.fields.get(key, ""))
