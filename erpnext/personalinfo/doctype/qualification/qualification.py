# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Qualification(Document):
   def validate(self):
      self.validation()

   def validation(self):
      data=frappe.db.sql("""
   
                   select qi.college
                   from `tabQualification` as q, `tabQualification Item` as qi
                   where q.name=qi.parent 
                  """)
      frappe.msgprint("college: {0}".format(college))
      return data
#  pass
# 	data = frappe.db.sql("""
# 	        # select *
				 
# 			# from `tabQualification` where name s


# 			# select item 
# 			# from `tabDesuung Sales` as ds, `tabSales Order Item` as soi
# 			# where ds.name = soi.parent
# 	""")
# 	return data