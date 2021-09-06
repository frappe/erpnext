# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):

	if not filters: filters = {}
	filters = frappe._dict(filters)

	columns = get_columns()

	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"label": _("Staffing Plan"),
			"fieldtype": "Link",
			"fieldname": "staffing_plan",
			"options": "Staffing Plan",
			"width": 150
		},
		{
			"label": _("Job Opening"),
			"fieldtype": "Link",
			"fieldname": "job_opening",
			"options": "Job Opening",
			"width": 105
		},
		{
			"label": _("Job Applicant"),
			"fieldtype": "Link",
			"fieldname": "job_applicant",
			"options": "Job Applicant",
			"width": 150
		},
		{
			"label": _("Applicant name"),
			"fieldtype": "data",
			"fieldname": "applicant_name",
			"width": 130
		},
		{
			"label": _("Application Status"),
			"fieldtype": "Data",
			"fieldname": "application_status",
			"width": 150
		},
		{
			"label": _("Job Offer"),
			"fieldtype": "Link",
			"fieldname": "job_offer",
			"options": "job Offer",
			"width": 150
		},
		{
			"label": _("Designation"),
			"fieldtype": "Data",
			"fieldname": "designation",
			"width": 100
		},
		{
			"label": _("Offer Date"),
			"fieldtype": "date",
			"fieldname": "offer_date",
			"width": 100
		},
		{
			"label": _("Job Offer status"),
			"fieldtype": "Data",
			"fieldname": "job_offer_status",
			"width": 150
		}
	]

def get_data(filters):
	data = []
	staffing_plan_details = get_staffing_plan(filters)
	staffing_plan_list  = list(set([details["name"] for details in staffing_plan_details]))
	sp_jo_map , jo_list = get_job_opening(staffing_plan_list)
	jo_ja_map , ja_list = get_job_applicant(jo_list)
	ja_joff_map = get_job_offer(ja_list)

	for sp in sp_jo_map.keys():
		parent_row = get_parent_row(sp_jo_map, sp, jo_ja_map, ja_joff_map)
		data += parent_row

	return data


def get_parent_row(sp_jo_map, sp, jo_ja_map, ja_joff_map):
	data = []
	if sp in sp_jo_map.keys():
		for jo in sp_jo_map[sp]:
			row = {
				"staffing_plan" : sp,
				"job_opening" : jo["name"],
			}
			data.append(row)
			child_row = get_child_row( jo["name"], jo_ja_map, ja_joff_map)
			data += child_row
	return data

def get_child_row(jo, jo_ja_map, ja_joff_map):
	data = []
	if jo in jo_ja_map.keys():
		for ja in jo_ja_map[jo]:
			row = {
				"indent":1,
				"job_applicant": ja.name,
				"applicant_name": ja.applicant_name,
				"application_status": ja.status,
			}
			if ja.name in ja_joff_map.keys():
				jo_detail =ja_joff_map[ja.name][0]
				row["job_offer"] = jo_detail.name
				row["job_offer_status"] = jo_detail.status
				row["offer_date"]= jo_detail.offer_date.strftime("%d-%m-%Y")
				row["designation"] = jo_detail.designation

			data.append(row)
	return data

def get_staffing_plan(filters):

	staffing_plan = frappe.db.sql("""
	select
		sp.name, sp.department, spd.designation, spd.vacancies, spd.current_count, spd.parent, sp.to_date
	from
		`tabStaffing Plan Detail` spd , `tabStaffing Plan` sp
	where
			spd.parent = sp.name
		And
			sp.to_date > '{0}'
		""".format(filters.on_date), as_dict = 1)

	return staffing_plan

def get_job_opening(sp_list):

	job_openings = frappe.get_all("Job Opening", filters = [["staffing_plan", "IN", sp_list]], fields =["name", "staffing_plan"])

	sp_jo_map = {}
	jo_list = []

	for openings in job_openings:
		if openings.staffing_plan not in sp_jo_map.keys():
			sp_jo_map[openings.staffing_plan] = [openings]
		else:
			sp_jo_map[openings.staffing_plan].append(openings)

		jo_list.append(openings.name)

	return sp_jo_map, jo_list

def get_job_applicant(jo_list):

	jo_ja_map = {}
	ja_list =[]

	applicants = frappe.get_all("Job Applicant", filters = [["job_title", "IN", jo_list]], fields =["name", "job_title","applicant_name", 'status'])

	for applicant in applicants:
		if applicant.job_title not in jo_ja_map.keys():
			jo_ja_map[applicant.job_title] = [applicant]
		else:
			jo_ja_map[applicant.job_title].append(applicant)

		ja_list.append(applicant.name)

	return jo_ja_map , ja_list

def get_job_offer(ja_list):
	ja_joff_map = {}

	offers = frappe.get_all("Job Offer", filters = [["job_applicant", "IN", ja_list]], fields =["name", "job_applicant", "status", 'offer_date', 'designation'])

	for offer in offers:
		if offer.job_applicant not in ja_joff_map.keys():
			ja_joff_map[offer.job_applicant] = [offer]
		else:
			ja_joff_map[offer.job_applicant].append(offer)

	return ja_joff_map
