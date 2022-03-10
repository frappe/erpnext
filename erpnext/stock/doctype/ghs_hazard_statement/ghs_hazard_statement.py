# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class GHSHazardStatement(Document):

	def before_save(self):
		newlist = frappe.db.get_list("Hazardous Material GHS Precautionary Statements", filters={"parent": self.name})
		newStr = []
		oldStr = []
		for x in range(len(newlist)):
			newS = str(newlist[x]).replace("{","").replace("'","").replace("name: ","").replace("}","")
			newStr.append(newS)
		for i in self.hazardous_material_ghs_precautionary_statements:
			oldStr.append(str(i.name))
		new = set(newStr)
		old = set(oldStr)
		if new != old:
			doc = frappe.db.get_list("Hazardous Material GHS Hazard Statements", {"ghs_hazard_statement": self.name },"parent")
			for x in range(len(doc)):
				s = str(doc[x]).replace("{","").replace("'","").replace("parent: ","").replace("}","")
				frappe.db.set_value("Hazardous Material", s, {"status": "Review"})
		else:
			pass
