# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def on_update(self):
		webnotes.conn.set_default("auto_accounting_for_stock", self.doc.auto_accounting_for_stock)
		
		if self.doc.auto_accounting_for_stock:
			warehouse_list = webnotes.conn.sql("select name, company from tabWarehouse", as_dict=1)
			warehouse_with_no_company = [d.name for d in warehouse_list if not d.company]
			if warehouse_with_no_company:
				webnotes.throw(_("Company is missing in following warehouses") + ": \n" + 
					"\n".join(warehouse_with_no_company))
			for wh in warehouse_list:
				wh_bean = webnotes.bean("Warehouse", wh.name)
				wh_bean.save()