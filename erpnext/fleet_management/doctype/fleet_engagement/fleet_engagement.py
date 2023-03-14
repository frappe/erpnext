# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint,getdate,time_diff_in_hours

class FleetEngagement(Document):
	def validate(self):
		self.calculate()

# var calculate_total_km = function(frm, cdt, cdn){
# 	let item = locals[cdt][cdn]
# 	if (flt(item.initial_km) > 0 and flt(item.final_km) > 0 ){
# 		if ( flt(item.initial_km) > flt(item.final_km)){
# 			frappe.throw("Initial KM Cannot be greater than finial KM")
# 		}
# 		item.total_km = flt(item.final_km) - flt(item.initial_km)
# 		frm.refresh_field("items")
# 	}
# }
	def calculate(self):
		for item in self.items:
			if item.trip_or_hole == "Hole":
				item.meterage_drilled = flt(item.hole_depth) * flt(item.no_of_holes)
			else:
				item.meterage_drilled = 0
			if cint(item.ignore_time) == 1:
				item.total_hours = item.total_km = 0
			else:
				if flt(item.initial_km) > 0 and flt(item.final_km) > 0:
					if flt(item.initial_km) > flt(item.final_km):
							frappe.throw("Initial KM Cannot be greater than finial KM")
					item.total_km = flt(item.final_km) - flt(item.initial_km)
				if item.end_time and item.start_time:
					item.total_hours = time_diff_in_hours( item.end_time, item.start_time)
					
		
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "Fleet Manager" in user_roles: 
		return

	return """(
		`tabFleet Engagement`.owner = '{user}'
		or 
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabFleet Engagement`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabFleet Engagement`.branch)
	)""".format(user=user)