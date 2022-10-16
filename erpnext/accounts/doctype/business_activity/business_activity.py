# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.desk.reportview import build_match_conditions

class BusinessActivity(Document):
	def validate(self):
		if self.is_default:
			def_ba = frappe.db.sql("select name from `tabBusiness Activity` where is_default = 1", as_dict=1)
			for a in def_ba:
				frappe.throw(str(a.name) + " is already set as default. Unset and Save again")

def get_default_ba():
	default_ba = frappe.db.sql("select name from `tabBusiness Activity` where is_default = 1", as_dict=1)
	default_ba = default_ba and default_ba[0].name or None	
	if not default_ba:
		frappe.throw("Define a default Business Activity")
	return default_ba	

#Show only not disabled business activities
def get_ba_list(doctype, txt, searchfield, start, page_len, filters):
	fields = ["name"]

	match_conditions = build_match_conditions("Business Activity")
	match_conditions = "and {}".format(match_conditions) if match_conditions else ""

	return frappe.db.sql("""select %s from `tabBusiness Activity` where is_disabled != 1
		and (%s like %s or name like %s)
		{match_conditions}
		order by
		case when name like %s then 0 else 1 end,
		name limit %s, %s""".format(match_conditions=match_conditions) %
		(", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s"),
		("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len))