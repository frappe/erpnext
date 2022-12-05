# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from frappe.utils import flt, cint,getdate,time_diff_in_hours
from frappe import _, qb, throw
from frappe.model.mapper import get_mapped_doc

class Logbook(Document):
	def validate(self):
		check_future_date(self.posting_date)
		self.check_duplicate_entry()
		self.check_date_validity()
		self.calculate_hours()
		self.calculate_downtime()
		self.validate_hours()

	def check_duplicate_entry(self):
		lb = qb.DocType("Logbook")
		dup_entry = (qb.from_(lb)
						.select(lb.name,lb.equipment,lb.posting_date)
						.where((lb.name != self.name) & (lb.equipment == self.equipment) & (lb.posting_date == self.posting_date))
						).run()
		if dup_entry:
			throw("Only one record per equipment per day is allowed. {0} already exists for {1} on {2}".format(frappe.bold(frappe.get_desk_link("Logbook", dup_entry[0][0])), dup_entry[0][1], dup_entry[0][2]))

	def check_date_validity(self):
		from_date, to_date = frappe.db.get_value("Equipment Hiring Form", self.equipment_hiring_form, ["start_date", "end_date"])
		if not getdate(from_date) <= getdate(self.posting_date) <= getdate(to_date):
			frappe.throw("Log Date should be between equipment hiring date {0} and {1}".format(from_date, to_date))
	
	def check_target_hour(self):
		if self.equipment_hiring_form:
			self.target_hours = frappe.db.get_value("Equipment Hiring Form", self.equipment_hiring_form, "target_hour")
		if flt(self.scheduled_working_hour) <= 0:
			frappe.throw("Scheduled Working Hour is mandatory")
		if flt(self.target_hours) <= 0:
			frappe.throw("Target Hour is mandatory")

	def validate_hours(self):
		difference = flt(self.total_hours) + flt(self.total_downtime_hours) - flt(self.scheduled_working_hour)
		if difference < 0:
			frappe.throw("Total of work hours ({0}) and downtime hours ({1}) should be equal to scheduled hours ({2})".format(frappe.bold(self.total_hours), frappe.bold(self.total_downtime_hours), frappe.bold(self.scheduled_working_hour)))
		if difference > 0:
			if flt(self.total_hours) + flt(self.total_downtime_hours) >= 24:
				frappe.throw("Total hours should be less than 24 hours")
			frappe.msgprint("<a style='color:red; font-size:large;'}><b>The total hours exceeds the scheduled working hour by "+str(difference)+" hours</b></a>")

	
	def calculate_hours(self):
		total_hours = ot_hours = 0
		for a in self.items:
			a.equipment = self.equipment
			if not a.uom:
				frappe.throw("Reading Unit is mandatory")
			if a.uom == "Trip":
				a.final_reading = 0
				if flt(a.initial_reading) > 0:
					if flt(a.target_trip) <= 0:
						frappe.throw("Target Trip is mandatory on row {0}".format(a.idx))
					a.hours = flt((flt(a.initial_reading )* flt(self.target_hours))) / flt(a.target_trip)
					total_hours += flt(round(a.hours,1))
					if cint(a.is_overtime):
						ot_hours += flt(a.hours)
				else:
					frappe.throw("Achieved Trip is mandatory")
			elif a.uom == "Hour":
				a.target_trip = 0
				if flt(a.reading_initial) >= 0 and flt(a.reading_final) >= 0:
					if flt(a.reading_initial) > flt(a.reading_final):
						frappe.throw("Final reading should not be smaller than inital")
					a.hours = flt(a.reading_final) - flt(a.reading_initial) - flt(a.idle_time)
					total_hours += flt(round(a.hours,1))
					if cint(a.is_overtime):
						ot_hours += a.hours 
				else:
					frappe.throw("Initial and Final Readings are mandatory")
			else:
				if a.initial_time and a.final_time:
					start = "{0} {1}".format(str(self.posting_date), str(a.initial_time))
					end = "{0} {1}".format(str(self.posting_date), str(a.final_time))
					if getdate(start) > getdate(end):
						frappe.throw("Final time should not be smaller than inital")
					a.hours = time_diff_in_hours(end, start) - flt(a.idle_time)
					if a.hours <= 0:
						frappe.throw("Difference of time and idle time should be more than 0")  
					total_hours += flt(round(a.hours,1))
					if cint(a.is_overtime):
						ot_hours += a.hours
				else:
					frappe.throw("Initial and Final Readings are mandatory")
		act_sch = self.scheduled_working_hour + 8
		if flt(total_hours) > flt(act_sch):
			frappe.throw("Total hours cannot be more than {0} hours".format(act_sch))

		self.total_hours = round(total_hours,1)
		self.total_ot = round(ot_hours,1)
	
	
	def calculate_downtime(self):
		total = 0
		for a in self.downtimes:
			a.equipment = self.equipment
			if flt(a.hours) <= 0:
				frappe.throw("Downtime hours should be greater than zero") 
			total += a.hours
		self.total_downtime_hours = total

