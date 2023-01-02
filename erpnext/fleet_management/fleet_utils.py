from __future__ import unicode_literals
import frappe
from frappe import _
from frappe import _, qb, throw
from frappe.utils import flt, cint,add_days, cstr, flt, getdate, nowdate, rounded, date_diff, get_datetime

##
# Both recieved and issued pols can be queried with this
##
def get_pol_till(purpose, equipment, posting_date, pol_type=None, posting_time="23:59:59"):
	if not equipment or not posting_date:
		frappe.throw("Equipment and Till Date are Mandatory")
	total = 0
	posting_datetime = str(get_datetime(str(posting_date) + ' ' + str(posting_time)))
	query = "select sum(ifnull(qty,0)) as total from `tabPOL Entry` where docstatus = 1 and type = \'"+str(purpose)+"\' and equipment = \'" + str(equipment) + "\' and cast(concat(posting_date, ' ' , posting_time) as datetime) <= \'" + str(posting_datetime) + "\'"
	if pol_type:
		query += " and pol_type = \'" + str(pol_type) + "\'"
	
	quantity = frappe.db.sql(query, as_dict=True)
	if quantity:
		total = quantity[0].total
	return total

def get_previous_km(purpose, equipment, posting_date, uom):
	pol_entry = qb.DocType("POL Entry")
	if not uom:
		uom = frappe.db.get_value("Equipment", equipment,"reading_uom")
	
	return (
				qb.from_(pol_entry)
				.select(pol_entry.current_km)
				.where((pol_entry.equipment == equipment) & (pol_entry.docstatus==1) & (pol_entry.uom == uom) & (pol_entry.type == purpose))
				.orderby( pol_entry.posting_date,order=qb.desc)
				.orderby( pol_entry.posting_time,order=qb.desc)
				.limit(1)
				.run()
				)


##
# Both recieved and issued pols can be queried with this
##
def get_pol_between(purpose, equipment, from_date, to_date, pol_type=None, own_cc=None):
	if not equipment or not from_date or not to_date:
		frappe.throw("Equipment and From/To Date are Mandatory")
	total = 0
	query = "select sum(qty) as total from `tabPOL Entry` where docstatus = 1 and type = \'"+str(purpose)+"\' and equipment = \'" + str(equipment) + "\' and date between \'" + str(from_date) + "\' and \'" + str(to_date) + "\'"
	if pol_type:
		query += " and pol_type = \'" + str(pol_type) + "\'"
	if own_cc:
		query += " and own_cost_center = 1"
		
	quantity = frappe.db.sql(query, as_dict=True)
	if quantity:
		total = quantity[0].total
	return total

##
# Get consumed POl as per yardstick
##
def get_pol_consumed_till(equipment, posting_date, posting_time="23:59:59", filter_dry=None):
	if not equipment or not posting_date:
				frappe.throw("Equipment and Till Date are Mandatory")
	posting_datetime = str(get_datetime(str(posting_date) + ' ' + str(posting_time)))

	if not filter_dry:
		pol = frappe.db.sql("select sum(consumption) as total from `tabLogbook` where docstatus = 1 and equipment = %s and cast(concat(to_date, ' ', to_time) as datetime) <= %s", (equipment, str(posting_datetime)), as_dict=True)
	else:
		pol = frappe.db.sql("select sum(consumption) as total from `tabLogbook` where docstatus = 1 and equipment = %s and rate_type = 'With Fuel' and cast(concat(to_date, ' ', to_time)  as datetime) <= %s", (equipment, str(posting_datetime) ), as_dict=True)
	if pol:
		return pol[0].total
	else:
		return 0	

def get_km_till(equipment, date):
	if not equipment or not date:
				frappe.throw("Equipment and Till Date are Mandatory")
	km = frappe.db.sql("select final_km from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and to_date <= %s order by final_km desc limit 1", (equipment, date), as_dict=True)
	if km:
		return km[0].final_km
	else:
		return 0	
	
def get_hour_till(equipment, date):
	if not equipment or not date:
				frappe.throw("Equipment and Till Date are Mandatory")
	hr = frappe.db.sql("select final_hour from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and to_date <= %s order by final_hour desc limit 1", (equipment, date), as_dict=True)
	if hr:
		return hr[0].final_hour
	else:
		return 0	



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_container_filtered(doctype, txt, searchfield, start, page_len, filters):
	cond = ""
	if filters and filters.get("branch"):
		cond = "and branch = '%s'" % filters.get("branch")

	return frappe.db.sql(
		"""select name, equipment_name, equipment_category, equipment_type from `tabEquipment` e
			where enabled = 1 and  `{key}` LIKE %(txt)s {cond}
			and exists (select 1 from `tabEquipment Type` where is_container = 1 and name = e.equipment_type and disabled = 0)
			order by name limit %(page_len)s offset %(start)s""".format(
			key=searchfield, cond=cond
		),
		{"txt": "%" + txt + "%", "start": start, "page_len": page_len},
	)