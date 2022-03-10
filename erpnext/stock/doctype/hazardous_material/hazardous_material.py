# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime

from six import text_type

class HazardousMaterial(Document):
	
	def on_change(self):
		lifecyclelist = frappe.db.get_list("Hazardous Material Company Use", {"parent": self.name }, "lifecycle")
		newvalue = frappe.db.get_value("Hazardous Material Company Use", {"parent": self.name}, "lifecycle")
		if lifecyclelist:
			lc = lifecyclelist[0]
			checker = True
			for x in lifecyclelist:
				if lc != x:
					checker = False
					break
			if checker == True:
				frappe.db.set_value("Hazardous Material",{"name": self.name}, {"lifecycle": newvalue})
		else:
			pass

		decommissioning_date = frappe.db.sql(""" Select max(decommissioning_date) from `tabHazardous Material Company Use` where parent=%s""", self.name)
		introduction_date = frappe.db.sql(""" Select min(introduction_date) from `tabHazardous Material Company Use` where parent=%s""", self.name)
		if decommissioning_date == ((None,),):
			pass
		else:	
			d_ds = str(decommissioning_date).replace("((datetime.date(","").replace("),),)","")
			d_dt = datetime.strptime(d_ds,'%Y, %m, %d')
			decommission_a = []
			for d_date in self.hazardous_material_company_use:
				decommission_a.append(d_date.decommissioning_date)
			if None in decommission_a:
				return False
			else:
				frappe.db.set_value("Hazardous Material",{"name": self.name}, {"decommissioning_date": d_dt})
				
		if introduction_date == ((None,),):
			pass
		else:
			i_ds = str(introduction_date).replace("((datetime.date(","").replace("),),)","")
			i_dt = datetime.strptime(i_ds,'%Y, %m, %d')
			introduction_a = []
			for d_date in self.hazardous_material_company_use:
				introduction_a.append(d_date.introduction_date)
			if None in introduction_a:
				pass
			else:
				frappe.db.set_value("Hazardous Material",{"name": self.name}, {"introduction_date": i_dt})

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		self.reload()

@frappe.whitelist()
def get_ghs_precautionary_statements(name):
    try:
        doc = frappe.get_doc('GHS Hazard Statement', name)
    except Exception as e:
        doc = None
        frappe.throw(_("Doctype Not Found"))
    return doc
