# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
    if filters.status == 'Free':
        return [
			_("Branch")+":Link/Branch:150",
			_("Equipment Number")+":Data:140",
			_("Equipment Model")+":Data:140",
			_("Equipment Type")+":Link/Equipment Type:120",
		]
    return [
        _("Reference")+":Link/Vehicle Request:100",
		_("EMP ID") + ":Link/Employee:80",
		_("Booked By")+":Data:100",
		_("Requested Date")+":Date:130",
		_("Equipment")+":Link/Equipment:100",
		_("Equipment Number")+":Data:120",
		_("Equipment Type")+":Link/Equipment Type:120",
		_("Operator ID")+":Link/Employee:80",
		_("Operator Name")+":Data:130",
		_("Operator Contact")+":Data:120",
		_("KM Reading") + ":Data:120",
		_("Previous KM") + ":Data:120",
		_("KM difference") + ":Data:120",
		_("From Date")+":Date:140",
		_("To Date")+":Date:140",
		_("Purpose")+":Data:120",
		_("Place of visit")+":Data:120"
	]
def get_data(filters):
    if filters.from_date > filters.to_date :
        frappe.throw("From Date cannot be before than To Date")
    cond = ''
    if filters.vehicle_type :
        cond += " AND vehicle_type = '{}'".format(filters.vehicle_type)
    if filters.branch:
        cond += "and branch='{}'".format(filters.branch)
    if filters.status == 'Free':
        return frappe.db.sql("""
			SELECT 
				e.branch,
       			e.name,
				e.equipment_model,
				e.equipment_type
			FROM `tabEquipment` e 
			WHERE NOT EXISTS (
				select vr.vehicle 
				from `tabVehicle Request` vr
				where 
				e.name = vr.vehicle_number
    			AND
				(vr.from_date BETWEEN '{0}' AND '{1}'
					OR vr.to_date BETWEEN '{0}' AND '{1}'
					OR '{0}' BETWEEN vr.from_date AND vr.to_date
					OR '{1}' BETWEEN vr.from_date AND vr.to_date
    			))
				{2}
            """.format(filters.from_date,filters.to_date,cond))
        
    return frappe.db.sql("""
		SELECT 
  			name,
			employee,
			employee_name,
			posting_date,vehicle,
			vehicle_number,
			vehicle_type,
			driver,
			driver_name,
			contact_number,
			kilometer_reading,
			previous_km,
			(kilometer_reading - previous_km) as kilometer_difference,
			from_date,
			to_date,
			purpose,
			place
		FROM
			`tabVehicle Request`
		WHERE
			(from_date BETWEEN '{0}' AND '{1}'
			OR to_date BETWEEN '{0}' AND '{1}'
			OR '{0}' BETWEEN from_date AND to_date
			OR '{1}' BETWEEN from_date AND to_date)
			AND docstatus = 1 
		{2}
            """.format(filters.from_date,filters.to_date,cond))