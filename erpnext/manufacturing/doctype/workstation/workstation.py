# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
from frappe.utils import flt

from frappe.model.document import Document

class Workstation(Document):
	def update_bom_operation(self):
		bom_list = frappe.db.sql("""select DISTINCT parent from `tabBOM Operation` 
			where workstation = %s""", self.name)
		for bom_no in bom_list:
			frappe.db.sql("""update `tabBOM Operation` set hour_rate = %s 
				where parent = %s and workstation = %s""", 
				(self.hour_rate, bom_no[0], self.name))
	
	def on_update(self):
		frappe.db.set(self, 'overhead', flt(self.hour_rate_electricity) + 
		flt(self.hour_rate_consumable) + flt(self.hour_rate_rent))
		frappe.db.set(self, 'hour_rate', flt(self.hour_rate_labour) + flt(self.overhead))
		self.update_bom_operation()

	def check_if_within_operating_hours(self, from_time, to_time):
		if self.check_workstation_for_operation_time(from_time, to_time):
			frappe.msgprint(_("Warning: Time Log timings outside workstation Operating Hours !"))

		msg = self.check_workstation_for_holiday(from_time, to_time)
		if msg != None:
			frappe.msgprint(msg)
					
	def check_workstation_for_operation_time(self, from_time, to_time):
		start_time = datetime.datetime.strptime(from_time,'%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')
		end_time = datetime.datetime.strptime(to_time,'%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')

		if frappe.db.sql("""select start_time, end_time from `tabWorkstation Operation Hours` 
			where parent = %s and (%s <start_time or %s > end_time )""",(self.workstation_name, start_time, end_time), as_dict=1):
			return 1

	def check_workstation_for_holiday(self, from_time, to_time):
		holiday_list = frappe.db.get_value("Workstation", self.workstation_name, "holiday_list")
		start_date = datetime.datetime.strptime(from_time,'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
		end_date = datetime.datetime.strptime(to_time,'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
		msg = _("Workstation is closed on the following dates as per Holiday List:")
		flag = 0
		for d in frappe.db.sql("""select holiday_date from `tabHoliday` where parent = %s and holiday_date between 
			%s and %s """,(holiday_list, start_date, end_date), as_dict=1):
			flag = 1
			msg = msg + "\n" + d.holiday_date 

		if flag ==1:
			return msg
		else: 
			return None