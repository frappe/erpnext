# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from typing import Dict, Optional, Tuple

import frappe
from frappe import _
from frappe.query_builder.functions import Max, Min, Sum
from frappe.utils import (
	add_days,
	cint,
	cstr,
	date_diff,
	flt,
	formatdate,
	get_fullname,
	get_link_to_form,
	getdate,
	nowdate,
)
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry
from erpnext.hr.utils import (
	get_holiday_dates_for_employee,
	get_leave_period,
	set_employee_name,
	share_doc_with_approver,
	get_employee_holidays,
	validate_active_employee,
)


class LeaveDayBlockedError(frappe.ValidationError):
	pass


class OverlapError(frappe.ValidationError):
	pass


class AttendanceAlreadyMarkedError(frappe.ValidationError):
	pass


class NotAnOptionalHoliday(frappe.ValidationError):
	pass


class InsufficientLeaveBalanceError(frappe.ValidationError):
	pass


class LeaveAcrossAllocationsError(frappe.ValidationError):
	pass


from frappe.model.document import Document


class LeaveApplication(Document):
	def get_feed(self):
		return _("{0}: From {0} of type {1}").format(self.employee_name, self.leave_type)

	def validate(self):
		validate_active_employee(self.employee)
		set_employee_name(self)
		self.validate_dates()
		self.validate_balance_leaves()
		self.validate_leave_overlap()
		self.validate_max_days()
		self.show_block_day_warning()
		self.validate_block_days()
		self.validate_salary_processed_days()
		# self.validate_attendance()
		self.set_half_day_date()
		self.validate_total_available()
		if frappe.db.get_value("Leave Type", self.leave_type, "is_optional_leave"):
			self.validate_optional_leave()
		self.validate_applicable_after()

	def on_update(self):
		if self.status == "Open" and self.docstatus < 1:
			# notify leave approver about creation
			if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
				self.notify_leave_approver()

		share_doc_with_approver(self, self.leave_approver)

	def on_submit(self):
		if self.status in ["Open", "Cancelled"]:
			frappe.throw(
				_("Only Leave Applications with status 'Approved' and 'Rejected' can be submitted")
			)

		self.validate_back_dated_application()
		self.update_attendance()

		# notify leave applier about approval
		if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
			self.notify_employee()

		self.create_leave_ledger_entry()
		self.reload()

	def before_cancel(self):
		self.status = "Cancelled"

	def on_cancel(self):
		self.create_leave_ledger_entry(submit=False)
		# notify leave applier about cancellation
		if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
			self.notify_employee()
		# self.cancel_attendance()

	def validate_applicable_after(self):
		if self.leave_type:
			leave_type = frappe.get_doc("Leave Type", self.leave_type)
			if leave_type.applicable_after > 0:
				date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
				leave_days = get_approved_leaves_for_period(
					self.employee, False, date_of_joining, self.from_date
				)
				number_of_days = date_diff(getdate(self.from_date), date_of_joining)
				if number_of_days >= 0:
					holidays = 0
					if not frappe.db.get_value("Leave Type", self.leave_type, "include_holiday"):
						holidays = get_holidays(self.employee, date_of_joining, self.from_date)
					number_of_days = number_of_days - leave_days - holidays
					if number_of_days < leave_type.applicable_after:
						frappe.throw(
							_("{0} applicable after {1} working days").format(
								self.leave_type, leave_type.applicable_after
							)
						)

	def validate_dates(self):
		if frappe.db.get_single_value("HR Settings", "restrict_backdated_leave_application"):
			if self.from_date and getdate(self.from_date) < getdate():
				allowed_role = frappe.db.get_single_value(
					"HR Settings", "role_allowed_to_create_backdated_leave_application"
				)
				user = frappe.get_doc("User", frappe.session.user)
				user_roles = [d.role for d in user.roles]
				if not allowed_role:
					frappe.throw(
						_("Backdated Leave Application is restricted. Please set the {} in {}").format(
							frappe.bold("Role Allowed to Create Backdated Leave Application"),
							get_link_to_form("HR Settings", "HR Settings"),
						)
					)

				if allowed_role and allowed_role not in user_roles:
					frappe.throw(
						_("Only users with the {0} role can create backdated leave applications").format(
							allowed_role
						)
					)

		if self.from_date and self.to_date and (getdate(self.to_date) < getdate(self.from_date)):
			frappe.throw(_("To date cannot be before from date"))

		if (
			self.half_day
			and self.half_day_date
			and (
				getdate(self.half_day_date) < getdate(self.from_date)
				or getdate(self.half_day_date) > getdate(self.to_date)
			)
		):

			frappe.throw(_("Half Day Date should be between From Date and To Date"))

		if not is_lwp(self.leave_type):
			self.validate_dates_across_allocation()
			self.validate_back_dated_application()

	def validate_dates_across_allocation(self):
		if frappe.db.get_value("Leave Type", self.leave_type, "allow_negative"):
			return

		alloc_on_from_date, alloc_on_to_date = self.get_allocation_based_on_application_dates()

		if not (alloc_on_from_date or alloc_on_to_date):
			frappe.throw(_("Application period cannot be outside leave allocation period"))
		elif self.is_separate_ledger_entry_required(alloc_on_from_date, alloc_on_to_date):
			frappe.throw(
				_("Application period cannot be across two allocation records"),
				exc=LeaveAcrossAllocationsError,
			)

	def get_allocation_based_on_application_dates(self) -> Tuple[Dict, Dict]:
		"""Returns allocation name, from and to dates for application dates"""

		def _get_leave_allocation_record(date):
			LeaveAllocation = frappe.qb.DocType("Leave Allocation")
			allocation = (
				frappe.qb.from_(LeaveAllocation)
				.select(LeaveAllocation.name, LeaveAllocation.from_date, LeaveAllocation.to_date)
				.where(
					(LeaveAllocation.employee == self.employee)
					& (LeaveAllocation.leave_type == self.leave_type)
					& (LeaveAllocation.docstatus == 1)
					& ((date >= LeaveAllocation.from_date) & (date <= LeaveAllocation.to_date))
				)
			).run(as_dict=True)

			return allocation and allocation[0]

		allocation_based_on_from_date = _get_leave_allocation_record(self.from_date)
		allocation_based_on_to_date = _get_leave_allocation_record(self.to_date)

		return allocation_based_on_from_date, allocation_based_on_to_date

	def validate_back_dated_application(self):
		future_allocation = frappe.db.sql(
			"""select name, from_date from `tabLeave Allocation`
			where employee=%s and leave_type=%s and docstatus=1 and from_date > %s
			and carry_forward=1""",
			(self.employee, self.leave_type, self.to_date),
			as_dict=1,
		)

		if future_allocation:
			frappe.throw(
				_(
					"Leave cannot be applied/cancelled before {0}, as leave balance has already been carry-forwarded in the future leave allocation record {1}"
				).format(formatdate(future_allocation[0].from_date), future_allocation[0].name)
			)



	def update_attendance(self):
		from datetime import datetime, timedelta
		if self.status != "Approved":
			return

		holiday_dates = []
		if not frappe.db.get_value("Leave Type", self.leave_type, "include_holiday"):
			holiday_dates = get_holiday_dates_for_employee(self.employee, self.from_date, self.to_date)
			# frappe.msgprint(str(holiday_dates))

		employee_holiday = []
		
		employee_holiday = get_employee_holidays(self.employee, self.from_date, self.to_date)
		# frappe.msgprint("***employee holidays*****"+str(employee_holiday))
		filtered_holidays = []
		for holiday in employee_holiday:
			date = holiday['holiday_date']
			weekly_off = holiday['weekly_off']
			filtered_holidays.append([date, {'weekly_off': weekly_off}])
		# frappe.msgprint("***employee holidays*****"+str(filtered_holidays))

#-----------------------------------------------------------------------------------------------------------------------
		lwp_dates = []
		leave_type_dates = []
		leave_dates = []
		if self.to_date == self.from_date:
			if self.half_day_date:
				if self.lwp_count >0:
					leave_dates.append((self.from_date, self.half_day_session, "lwp"))
				else:
					leave_dates.append((self.from_date, self.half_day_session, "leave_type"))
		
			else:
				if self.lwp_count >0:
					leave_dates.append((self.from_date, "session1", "lwp"))
					leave_dates.append((self.from_date, "session2", "lwp"))
				else:
					leave_dates.append((self.from_date, "session1", "leave_type"))
					leave_dates.append((self.from_date, "session2", "leave_type"))

			#---------------------------------------------------------------------------
		else:
			tot_leave_sessions = self.total_leave_days *2
			if self.half_day_date:
				if self.half_day_date == self.to_date:
					lwp_sessions = self.lwp_count *2
					leave_sessions = tot_leave_sessions - lwp_sessions
					leave_days_current = leave_sessions/2
					
					if leave_days_current > 0:
						if int(leave_days_current) ==  leave_days_current:
							my_counter = leave_days_current
							from_date_is_wo = False
							to_date_is_wo = False
							for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								# if date in holiday_dates:
								# 	continue
								should_continue = False
								weekly_off = False
								
								for holiday in filtered_holidays:
									holiday_date, weekly_off_info = holiday
									if self.to_date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("weekly_off"+str(weekly_off_info))
										if weekly_off_info.get('weekly_off') == 1:
											to_date_is_wo = True
									if date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("#########"+str(date))
										should_continue = True
										if weekly_off_info.get('weekly_off') == 1:
											weekly_off = True
											should_continue = False
										break
								if date == self.from_date and weekly_off == True:
									# frappe.msgprint("from date continue:"+str(date))
									should_continue =True
									from_date_is_wo = True
								elif date == (getdate(self.from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
									# frappe.msgprint("for +1:"+str(date))
									should_continue =True
								elif date == self.to_date and weekly_off:
									should_continue = True
								elif date == (getdate(self.to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
									should_continue = True
								if should_continue == True:
									continue

								
								
								if my_counter > 0:
									leave_dates.append((date,'session1',"leave type"))
									leave_dates.append((date,'session2',"leave type"))
									my_counter -= 1

								else:
									if dt == self.to_date:       # check for proper variable to match
										leave_dates.append((date,'session1',"lwp"))
									else:
										leave_dates.append((date,'session1',"lwp"))
										leave_dates.append((date,'session2',"lwp"))
						else:
							my_counter = int(leave_days_current) + 1
							from_date_is_wo = False
							to_date_is_wo = False
							for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								# if date in holiday_dates:
								# 	continue
				
								should_continue = False
								weekly_off = False
								
								for holiday in filtered_holidays:
									holiday_date, weekly_off_info = holiday
									if self.to_date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("weekly_off"+str(weekly_off_info))
										if weekly_off_info.get('weekly_off') == 1:
											to_date_is_wo = True
									if date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("****Date****"+str(date))
										should_continue = True
										if weekly_off_info.get('weekly_off') == 1:
											weekly_off = True
											should_continue = False
										break
								if date == self.from_date and weekly_off == True:
									# frappe.msgprint("from date continue:"+str(date))
									should_continue =True
									from_date_is_wo = True
								elif date == (getdate(self.from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
									# frappe.msgprint("for +1:"+str(date))
									should_continue =True
								elif date == self.to_date and weekly_off:
									should_continue = True
								elif date == (getdate(self.to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
									should_continue = True
								if should_continue == True:
									continue
								if my_counter > 0:
									if my_counter == 1:
										if self.lwp_count == 0:
											leave_dates.append((date,"session1","leave type"))
										else:
											leave_dates.append((date,'session1',"leave type"))
											leave_dates.append((date,'session2',"lwp")) 
										# leave_dates.append((date,"session2","lwp"))
									else:
										leave_dates.append((date,"session1","leave type"))
										leave_dates.append((date,"session2","leave type"))
									my_counter -=1

								else:
									if str(dt) == str(self.to_date): 
										
										      # check for proper variable to match
										leave_dates.append((date,'session1',"lwp"))
									else:
										leave_dates.append((date,'session1',"lwp"))
										leave_dates.append((date,'session2',"lwp"))
					else:
						from_date_is_wo = False
						to_date_is_wo = False
						for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								# if date in holiday_dates:
								# 	continue
								should_continue = False
								weekly_off = False
								
								for holiday in filtered_holidays:
									holiday_date, weekly_off_info = holiday
									if self.to_date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("weekly_off"+str(weekly_off_info))
										if weekly_off_info.get('weekly_off') == 1:
											to_date_is_wo = True
									if date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("#########"+str(date))
										should_continue = True
										if weekly_off_info.get('weekly_off') == 1:
											weekly_off = True
											should_continue = False
										break
								if date == self.from_date and weekly_off == True:
									# frappe.msgprint("from date continue:"+str(date))
									should_continue =True
									from_date_is_wo = True
								elif date == (getdate(self.from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
									# frappe.msgprint("for +1:"+str(date))
									should_continue =True
								elif date == self.to_date and weekly_off:
									should_continue = True
								elif date == (getdate(self.to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
									should_continue = True
								if should_continue == True:
									continue
								if str(dt) == str(self.to_date):       # check for proper variable to match
										leave_dates.append((date,'session1',"lwp"))

								else:
									leave_dates.append((date,'session1',"lwp"))
									leave_dates.append((date,'session2',"lwp"))
				else:

					lwp_sessions = self.lwp_count *2
					leave_sessions = tot_leave_sessions - lwp_sessions
					leave_days_current = leave_sessions/2
					if leave_days_current > 0:
						my_counter = leave_days_current
						from_date_is_wo = False
						to_date_is_wo = False
						for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
							date = dt.strftime("%Y-%m-%d")
							# if date in holiday_dates:
							# 		continue
							should_continue = False
							weekly_off = False
							
							for holiday in filtered_holidays:
								holiday_date, weekly_off_info = holiday
								if self.to_date == holiday_date.strftime("%Y-%m-%d"):
									# frappe.msgprint("weekly_off"+str(weekly_off_info))
									if weekly_off_info.get('weekly_off') == 1:
										to_date_is_wo = True
								if date == holiday_date.strftime("%Y-%m-%d"):
									# frappe.msgprint("#########"+str(date))
									should_continue = True
									if weekly_off_info.get('weekly_off') == 1:
										weekly_off = True
										should_continue = False
									break
							if date == self.from_date and weekly_off == True:
								# frappe.msgprint("from date continue:"+str(date))
								should_continue =True
								from_date_is_wo = True
							elif date == (getdate(self.from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
								# frappe.msgprint("for +1:"+str(date))
								should_continue =True
							elif date == self.to_date and weekly_off:
								should_continue = True
							elif date == (getdate(self.to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
								should_continue = True
							if should_continue == True:
								continue
							
							
							if  str(dt) == str(self.from_date):      # check for proper variable to match
								leave_dates.append((date,"session2","leave_type"))
								my_counter = my_counter - 0.5 
							else:
								if my_counter > 0:
									if int(my_counter) == my_counter:
										leave_dates.append((date,'session1',"leave type"))
										leave_dates.append((date,'session2',"leave type"))
										my_counter -=1
									else:
										if int(my_counter) == 0:
											leave_dates.append((date,'session1',"leave type"))
											leave_dates.append((date,'session2',"lwp"))
										else:
											leave_dates.append((date,'session1',"leave type"))
											leave_dates.append((date,'session2',"leave_type"))
										my_counter -=1

								else:
									leave_dates.append((date,'session1',"lwp"))
									leave_dates.append((date,'session2',"lwp"))

					else:
						from_date_is_wo = False
						to_date_is_wo = False
						for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								# if date in holiday_dates:
								# 	continue
								should_continue = False
								weekly_off = False
							
								for holiday in filtered_holidays:
									holiday_date, weekly_off_info = holiday
									if self.to_date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("weekly_off"+str(weekly_off_info))
										if weekly_off_info.get('weekly_off') == 1:
											to_date_is_wo = True
									if date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("#########"+str(date))
										should_continue = True
										if weekly_off_info.get('weekly_off') == 1:
											weekly_off = True
											should_continue = False
										break
								if date == self.from_date and weekly_off == True:
									# frappe.msgprint("from date continue:"+str(date))
									should_continue =True
									from_date_is_wo = True
								elif date == (getdate(self.from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
									# frappe.msgprint("for +1:"+str(date))
									should_continue =True
								elif date == self.to_date and weekly_off:
									should_continue = True
								elif date == (getdate(self.to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
									should_continue = True
								if should_continue == True:
									continue
								
								if str(dt) == str(self.from_date):       # check for proper variable to match
										leave_dates.append((date,'session2',"lwp"))

								else:
									leave_dates.append((date,'session1',"lwp"))
									leave_dates.append((date,'session2',"lwp"))
			else:
				lwp_sessions = self.lwp_count *2
				# frappe.msgprint("lwp_sessions: " + str(lwp_sessions))
				leave_sessions = tot_leave_sessions - lwp_sessions
				leave_days_current = leave_sessions/2
				# frappe.msgprint("leave_days_current: " + str(leave_days_current))
				if leave_days_current > 0:
					if int(leave_days_current) ==  leave_days_current:
						my_counter = leave_days_current
						from_date_is_wo = False
						to_date_is_wo = False
						for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
							date = dt.strftime("%Y-%m-%d")
							# if date in holiday_dates:
							# 		continue
							should_continue = False
							weekly_off = False
							
							for holiday in filtered_holidays:
								holiday_date, weekly_off_info = holiday
								if self.to_date == holiday_date.strftime("%Y-%m-%d"):
									# frappe.msgprint("weekly_off"+str(weekly_off_info))
									if weekly_off_info.get('weekly_off') == 1:
										to_date_is_wo = True
								if date == holiday_date.strftime("%Y-%m-%d"):
									# frappe.msgprint("#########"+str(date))
									should_continue = True
									if weekly_off_info.get('weekly_off') == 1:
										weekly_off = True
										should_continue = False
									break
							if date == self.from_date and weekly_off == True:
								# frappe.msgprint("from date continue:"+str(date))
								should_continue =True
								from_date_is_wo = True
							elif date == (getdate(self.from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
								# frappe.msgprint("for +1:"+str(date))
								should_continue =True
							elif date == self.to_date and weekly_off:
								should_continue = True
							elif date == (getdate(self.to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
								should_continue = True
							if should_continue == True:
								continue
								
							if my_counter > 0:
								leave_dates.append((date,'session1',"leave type"))
								leave_dates.append((date,'session2',"leave type"))
								my_counter -= 1
							else:

								leave_dates.append((date,'session1',"lwp"))
								leave_dates.append((date,'session2',"lwp"))
				
					else:
							my_counter = int(leave_days_current) + 1
							from_date_is_wo = False
							to_date_is_wo = False
							for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								# if date in holiday_dates:
								# 	continue
								should_continue = False
								weekly_off = False
							
								for holiday in filtered_holidays:
									holiday_date, weekly_off_info = holiday
									if self.to_date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("weekly_off"+str(weekly_off_info))
										if weekly_off_info.get('weekly_off') == 1:
											to_date_is_wo = True
									if date == holiday_date.strftime("%Y-%m-%d"):
										# frappe.msgprint("#########"+str(date))
										should_continue = True
										if weekly_off_info.get('weekly_off') == 1:
											weekly_off = True
											should_continue = False
										break
								if date == self.from_date and weekly_off == True:
									# frappe.msgprint("from date continue:"+str(date))
									should_continue =True
									from_date_is_wo = True
								elif date == (getdate(self.from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
									# frappe.msgprint("for +1:"+str(date))
									should_continue =True
								elif date == self.to_date and weekly_off:
									should_continue = True
								elif date == (getdate(self.to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
									should_continue = True
								if should_continue == True:
									continue
								if my_counter > 0:
									if my_counter == 1:
										leave_dates.append((date,"session1","leave type"))  
										leave_dates.append((date,"session2","lwp"))
									else:
										leave_dates.append((date,"session1","leave type"))
										leave_dates.append((date,"session2","leave type"))
									my_counter -=1			
								else:
									leave_dates.append((date,'session1',"lwp"))
									leave_dates.append((date,'session2',"lwp"))
				else:
					from_date_is_wo = False
					to_date_is_wo = False
					for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
							date = dt.strftime("%Y-%m-%d")
							# if date in holiday_dates:
							# 		continue
							should_continue = False
							weekly_off = False
							
							for holiday in filtered_holidays:
								holiday_date, weekly_off_info = holiday
								if self.to_date == holiday_date.strftime("%Y-%m-%d"):
									# frappe.msgprint("weekly_off"+str(weekly_off_info))
									if weekly_off_info.get('weekly_off') == 1:
										to_date_is_wo = True
								if date == holiday_date.strftime("%Y-%m-%d"):
									# frappe.msgprint("#########"+str(date))
									should_continue = True
									if weekly_off_info.get('weekly_off') == 1:
										weekly_off = True
										should_continue = False
									break
							if date == self.from_date and weekly_off == True:
								# frappe.msgprint("from date continue:"+str(date))
								should_continue =True
								from_date_is_wo = True
							elif date == (getdate(self.from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
								# frappe.msgprint("for +1:"+str(date))
								should_continue =True
							elif date == self.to_date and weekly_off:
								should_continue = True
							elif date == (getdate(self.to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
								should_continue = True
							if should_continue == True:
								continue
							leave_dates.append((date,'session1',"lwp"))
							leave_dates.append((date,'session2',"lwp"))


		# frappe.msgprint("Selected Leave Dates: " + str(leave_dates))
		for date, session, leave_type in leave_dates:
			if leave_type == 'lwp':
				lwp_dates.append(date)
			else:
				leave_type_dates.append(date)
		unique_lwp_dates_set = set(lwp_dates)
		unique_leave_type_dates_set = set(leave_type_dates)
		unique_lwp_dates = list(unique_lwp_dates_set)
		unique_leave_type_dates = list(unique_leave_type_dates_set)
		# frappe.msgprint("lwp"+str(unique_lwp_dates))
		# frappe.msgprint("leave type"+str(unique_leave_type_dates))

		for selected_leave in unique_leave_type_dates:
			attendance_name = frappe.db.exists(
				"Attendance", dict(employee=self.employee, attendance_date=unique_leave_type_dates, docstatus=("!=", 2))
			)

			# don't mark attendance for holidays
			# if leave type does not include holidays within leaves as leaves
			# if selected_leave in holiday_dates:
			# 	if attendance_name:
			# 		# cancel and delete existing attendance for holidays
			# 		attendance = frappe.get_doc("Attendance", attendance_name)
			# 		attendance.flags.ignore_permissions = True
			# 		if attendance.docstatus == 1:
			# 			attendance.cancel()
			# 		frappe.delete_doc("Attendance", attendance_name, force=1)
			# 	continue

			self.create_or_update_attendance(attendance_name, selected_leave , leave_dates)

		for lwp_date in unique_lwp_dates:
			
			attendance_name = frappe.db.exists(
				"Attendance", dict(employee=self.employee, attendance_date=unique_lwp_dates, docstatus=("!=", 2))
			)

			# don't mark attendance for holidays
			# if leave type does not include holidays within leaves as leaves
			# if lwp_date in holiday_dates:
			# 	if attendance_name:
			# 		# cancel and delete existing attendance for holidays
			# 		attendance = frappe.get_doc("Attendance", attendance_name)
			# 		attendance.flags.ignore_permissions = True
			# 		if attendance.docstatus == 1:
			# 			attendance.cancel()
			# 		frappe.delete_doc("Attendance", attendance_name, force=1)
			# 	continue

			self.create_or_update_attendance_lwp(attendance_name, lwp_date, leave_dates)
		return unique_lwp_dates, unique_leave_type_dates


	def create_or_update_attendance(self, attendance_name, selected_leave, leave_dates):
		status = (
			"Half Day"
			if self.half_day_date and getdate(selected_leave) == getdate(self.half_day_date)
			else "On Leave"
		)
		session =None
		session_to_set = None
		for date, session,leave_type in leave_dates:
			if date == self.half_day_date and leave_type == 'leave_type':
				matching_leave = (date, session, leave_type)
				session_to_set = session
				break
		common_date = []
		date_leave_types = {}
		for date, session, leave_type in leave_dates:
			if date in date_leave_types:
				date_leave_types[date].add(leave_type)
			else:
				date_leave_types[date] = {leave_type}
		for date, leave_types in date_leave_types.items():
			if len(leave_types) > 1:
				leave_type_set = set()
				for entry in leave_dates:
					if entry[0] == date:
						leave_type_set.add(entry[2])
						common_date.append(entry)
		filtered_common_date = [entry for entry in common_date if entry[2] == 'leave type']
		date_value = None
		session_value = None
		for entry in filtered_common_date:
			date_value, session_value, leave_type_value = entry
		# frappe.msgprint('Date Value: ' + str(date_value))
		# frappe.msgprint('Session Value: ' + str(session_value))
		# status = (
		# 	"Half Day"
		# 	if selected_leave == date_value
		# 	else "On Leave"
		# )

		

		# make new attendance and submit it
		doc = frappe.new_doc("Attendance")
		doc.employee = self.employee
		doc.employee_name = self.employee_name
		doc.attendance_date = selected_leave
		doc.company = self.company
		doc.leave_type = self.leave_type
		doc.leave_application = self.name
		doc.status = status
		if selected_leave == self.half_day_date:
			doc.half_day_session = session_to_set
		if selected_leave == date_value:
			doc.half_day_session = session_value
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		doc.submit()

	def create_or_update_attendance_lwp(self, attendance_name, lwp_date, leave_dates):
		status = (
			"Half Day"
			if self.half_day_date and getdate(lwp_date) == getdate(self.half_day_date)
			else "On Leave"
		)

		session =None
		session_to_set = None
		for date, session,leave_type in leave_dates:
			if date == self.half_day_date and leave_type == 'lwp':
				matching_leave = (date, session, leave_type)
				session_to_set = session
				break
		common_date = []
		date_leave_types = {}
		for date, session, leave_type in leave_dates:
			if date in date_leave_types:
				date_leave_types[date].add(leave_type)
			else:
				date_leave_types[date] = {leave_type}
		for date, leave_types in date_leave_types.items():
			if len(leave_types) > 1:
				leave_type_set = set()
				for entry in leave_dates:
					if entry[0] == date:
						leave_type_set.add(entry[2])
						common_date.append(entry)
		filtered_common_date = [entry for entry in common_date if entry[2] == 'lwp']
		date_value = None
		session_value = None
		for entry in filtered_common_date:
			date_value, session_value, leave_type_value = entry
		# frappe.msgprint('Date Value: ' + str(date_value))
		# frappe.msgprint('Session Value: ' + str(session_value))
		# status = (
		# 	"Half Day"
		# 	if lwp_date == date_value
		# 	else "On Leave"
		# )

	
		doc = frappe.new_doc("Attendance")
		doc.employee = self.employee
		doc.employee_name = self.employee_name
		doc.attendance_date = lwp_date
		doc.company = self.company
		doc.leave_type = 'Leave Without Pay'
		doc.leave_application = self.name
		doc.status = status
		if lwp_date == self.half_day_date:
			doc.half_day_session = session_to_set
		if lwp_date == date_value:
			doc.half_day_session = session_value
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		doc.submit()
				


	# def cancel_attendance(self):
	# 	if self.docstatus == 2:
	# 		attendance = frappe.db.sql(
	# 			"""select name from `tabAttendance` where employee = %s\
	# 			and (attendance_date between %s and %s) and docstatus < 2 and status in ('On Leave', 'Half Day')""",
	# 			(self.employee, self.from_date, self.to_date),
	# 			as_dict=1,
	# 		)
	# 		for name in attendance:
	# 			frappe.db.set_value("Attendance", name, "docstatus", 2)

	def validate_salary_processed_days(self):
		if not frappe.db.get_value("Leave Type", self.leave_type, "is_lwp"):
			return

		last_processed_pay_slip = frappe.db.sql(
			"""
			select start_date, end_date from `tabSalary Slip`
			where docstatus = 1 and employee = %s
			and ((%s between start_date and end_date) or (%s between start_date and end_date))
			order by modified desc limit 1
		""",
			(self.employee, self.to_date, self.from_date),
		)

		if last_processed_pay_slip:
			frappe.throw(
				_(
					"Salary already processed for period between {0} and {1}, Leave application period cannot be between this date range."
				).format(
					formatdate(last_processed_pay_slip[0][0]), formatdate(last_processed_pay_slip[0][1])
				)
			)

	def show_block_day_warning(self):
		block_dates = get_applicable_block_dates(
			self.from_date, self.to_date, self.employee, self.company, all_lists=True
		)

		if block_dates:
			frappe.msgprint(_("Warning: Leave application contains following block dates") + ":")
			for d in block_dates:
				frappe.msgprint(formatdate(d.block_date) + ": " + d.reason)

	def validate_block_days(self):
		block_dates = get_applicable_block_dates(
			self.from_date, self.to_date, self.employee, self.company
		)

		if block_dates and self.status == "Approved":
			frappe.throw(_("You are not authorized to approve leaves on Block Dates"), LeaveDayBlockedError)

	def validate_balance_leaves(self):
		if self.from_date and self.to_date:
			self.total_leave_days = get_number_of_leave_days(
				self.employee, self.leave_type, self.from_date, self.to_date, self.half_day, self.half_day_date
			)

			if self.total_leave_days <= 0:
				frappe.throw(
					_(
						"The day(s) on which you are applying for leave are holidays. You need not apply for leave."
					)
				)

			if not is_lwp(self.leave_type):
				leave_balance = get_leave_balance_on(
					self.employee,
					self.leave_type,
					self.from_date,
					self.to_date,
					consider_all_leaves_in_the_allocation_period=True,
					for_consumption=True,
				)
				self.leave_balance = leave_balance.get("leave_balance")
				leave_balance_for_consumption = leave_balance.get("leave_balance_for_consumption")
				# frappe.msgprint(str(leave_balance_for_consumption))

				if self.status != "Rejected" and (
					leave_balance_for_consumption < self.current_leave_type_count or not leave_balance_for_consumption
				):
					self.show_insufficient_balance_message(leave_balance_for_consumption)

	def show_insufficient_balance_message(self, leave_balance_for_consumption: float) -> None:
		alloc_on_from_date, alloc_on_to_date = self.get_allocation_based_on_application_dates()
		employee_leave_types = frappe.get_all("Leave Allocation", filters={"employee": self.employee}, pluck="leave_type")
		msg = _("Insufficient leave balance for Leave Type {0}").format(frappe.bold(self.leave_type))
		msg += "<br>"
		available_leave_types=[]
		for leave_type in employee_leave_types:
			if leave_type == self.leave_type:
				continue  # Skip the current leave type
			balance = get_leave_balance_on(
            self.employee,
            leave_type,
            self.from_date,
            self.to_date,
            consider_all_leaves_in_the_allocation_period=True,
            for_consumption=True,
        )
			available_balance = balance.get("leave_balance_for_consumption")
			if available_balance > 0:
				available_leave_types.append(f"{leave_type}")
		if available_leave_types:
			msg += _(" You can take leaves from these leave types:")
			msg += "<br>"
			msg += "<br>".join("* " + leave for leave in available_leave_types)
		frappe.throw(
			msg,
			exc=InsufficientLeaveBalanceError,
			title=_("Insufficient Balance"),
			)


	def validate_leave_overlap(self):
		if not self.name:
			# hack! if name is null, it could cause problems with !=
			self.name = "New Leave Application"

		for d in frappe.db.sql(
			"""
			select
				name, leave_type, posting_date, from_date, to_date, total_leave_days, half_day_date , half_day_session
			from `tabLeave Application`
			where employee = %(employee)s and docstatus < 2 and status in ("Open", "Approved")
			and to_date >= %(from_date)s and from_date <= %(to_date)s
			and name != %(name)s""",
			{
				"employee": self.employee,
				"from_date": self.from_date,
				"to_date": self.to_date,
				"half_day_session": self.half_day_session,
				"name": self.name,
			},
			as_dict=1,
		):
			# frappe.msgprint("Checking for overlap with:\n"
            #     "half_day_session: {}\n"
            #     "d.half_day_session: {}".format(self.half_day_session, d.half_day_session))


			if (
				cint(self.half_day) == 1
				and getdate(self.half_day_date) == getdate(d.half_day_date)
				and (
					flt(self.total_leave_days) == 0.5
					or getdate(self.from_date) == getdate(d.to_date)
					or getdate(self.to_date) == getdate(d.from_date)
				)
				and self.half_day_session != d.half_day_session
			):

				total_leaves_on_half_day = self.get_total_leaves_on_half_day()
				if total_leaves_on_half_day >= 1:
					self.throw_overlap_error(d)
			else:
				self.throw_overlap_error(d)



	def throw_overlap_error(self, d):
		form_link = get_link_to_form("Leave Application", d.name)
		msg = _("Employee {0} has already applied for {1} between {2} and {3} : {4}").format(
			self.employee, d["leave_type"], formatdate(d["from_date"]), formatdate(d["to_date"]), form_link
		)
		frappe.throw(msg, OverlapError)

	def get_total_leaves_on_half_day(self):
		leave_count_on_half_day_date = frappe.db.sql(
			"""select count(name) from `tabLeave Application`
			where employee = %(employee)s
			and docstatus < 2
			and status in ("Open", "Approved")
			and half_day = 1
			and half_day_date = %(half_day_date)s
			and name != %(name)s""",
			{"employee": self.employee, "half_day_date": self.half_day_date, "name": self.name},
		)[0][0]

		return leave_count_on_half_day_date * 0.5

	def validate_total_available(self):
		max_days = self.total_available
		max_days = float(max_days)
		if max_days and (self.total_leave_days > max_days):
			frappe.msgprint(_("You have {0} available leave days this month. considering {1} days as Leave Without Pay (LWP)").format(self.total_available, self.lwp_count))

	
	def validate_max_days(self):
		max_days = frappe.db.get_value("Leave Type", self.leave_type, "max_continuous_days_allowed")
		if max_days and self.total_leave_days > cint(max_days):
			frappe.throw(_("Leave of type {0} cannot be longer than {1}").format(self.leave_type, max_days))

	# def validate_attendance(self):
	# 	attendance = frappe.db.sql(
	# 		"""select name from `tabAttendance` where employee = %s and (attendance_date between %s and %s)
	# 				and status = "Present" and docstatus = 1""",
	# 		(self.employee, self.from_date, self.to_date),
	# 	)
	# 	if attendance:
	# 		frappe.throw(
	# 			_("Attendance for employee {0} is already marked for this day").format(self.employee),
	# 			AttendanceAlreadyMarkedError,
	# 		)

	def validate_optional_leave(self):
		leave_period = get_leave_period(self.from_date, self.to_date, self.company)
		if not leave_period:
			frappe.throw(_("Cannot find active Leave Period"))
		optional_holiday_list = frappe.db.get_value(
			"Leave Period", leave_period[0]["name"], "optional_holiday_list"
		)
		if not optional_holiday_list:
			frappe.throw(
				_("Optional Holiday List not set for leave period {0}").format(leave_period[0]["name"])
			)
		day = getdate(self.from_date)
		while day <= getdate(self.to_date):
			if not frappe.db.exists(
				{"doctype": "Holiday", "parent": optional_holiday_list, "holiday_date": day}
			):
				frappe.throw(
					_("{0} is not in Optional Holiday List").format(formatdate(day)), NotAnOptionalHoliday
				)
			day = add_days(day, 1)

	def set_half_day_date(self):
		if self.from_date == self.to_date and self.half_day == 1:
			self.half_day_date = self.from_date
		elif self.half_day == 0:
			self.half_day_date = None
		else:
			self.half_day_date = self.from_date if self.half_day_date == self.from_date else self.to_date


	def notify_employee(self):
		employee = frappe.get_doc("Employee", self.employee)
		if not employee.user_id:
			return

		parent_doc = frappe.get_doc("Leave Application", self.name)
		args = parent_doc.as_dict()

		template = frappe.db.get_single_value("HR Settings", "leave_status_notification_template")
		if not template:
			frappe.msgprint(_("Please set default template for Leave Status Notification in HR Settings."))
			return
		email_template = frappe.get_doc("Email Template", template)
		message = frappe.render_template(email_template.response, args)

		self.notify(
			{
				# for post in messages
				"message": message,
				"message_to": employee.user_id,
				# for email
				"subject": email_template.subject,
				"notify": "employee",
			}
		)

	def notify_leave_approver(self):
		if self.leave_approver:
			parent_doc = frappe.get_doc("Leave Application", self.name)
			args = parent_doc.as_dict()

			template = frappe.db.get_single_value("HR Settings", "leave_approval_notification_template")
			if not template:
				frappe.msgprint(
					_("Please set default template for Leave Approval Notification in HR Settings.")
				)
				return
			email_template = frappe.get_doc("Email Template", template)
			message = frappe.render_template(email_template.response, args)

			self.notify(
				{
					# for post in messages
					"message": message,
					"message_to": self.leave_approver,
					# for email
					"subject": email_template.subject,
				}
			)

	def notify(self, args):
		args = frappe._dict(args)
		# args -> message, message_to, subject
		if cint(self.follow_via_email):
			contact = args.message_to
			if not isinstance(contact, list):
				if not args.notify == "employee":
					contact = frappe.get_doc("User", contact).email or contact

			sender = dict()
			sender["email"] = frappe.get_doc("User", frappe.session.user).email
			sender["full_name"] = get_fullname(sender["email"])

			try:
				frappe.sendmail(
					recipients=contact,
					sender=sender["email"],
					subject=args.subject,
					message=args.message,
				)
				frappe.msgprint(_("Email sent to {0}").format(contact))
			except frappe.OutgoingEmailError:
				pass
	def calculate_unique_dates(self):
		holiday_dates = []
		if not frappe.db.get_value("Leave Type", self.leave_type, "include_holiday"):
			holiday_dates = get_holiday_dates_for_employee(self.employee, self.from_date, self.to_date)
			# frappe.msgprint(str(holiday_dates))
		lwp_dates = []
		leave_type_dates = []
		leave_dates = []
		if self.to_date == self.from_date:
			if self.half_day_date:
				if self.lwp_count >0:
					leave_dates.append((self.from_date, self.half_day_session, "lwp"))
				else:
					leave_dates.append((self.from_date, self.half_day_session, "leave_type"))
		
			else:
				if self.lwp_count >0:
					leave_dates.append((self.from_date, "session1", "lwp"))
					leave_dates.append((self.from_date, "session2", "lwp"))
				else:
					leave_dates.append((self.from_date, "session1", "leave_type"))
					leave_dates.append((self.from_date, "session2", "leave_type"))

			#---------------------------------------------------------------------------
		else:
			tot_leave_sessions = self.total_leave_days *2
			if self.half_day_date:

				# frappe.msgprint("tot_leave_sessions: " + str(tot_leave_sessions))
				if self.half_day_date == self.to_date:
					# frappe.msgprint(str(self.to_date))
					lwp_sessions = self.lwp_count *2
					# frappe.msgprint("lwp_sessions: " + str(lwp_sessions))
					leave_sessions = tot_leave_sessions - lwp_sessions
					leave_days_current = leave_sessions/2
					# frappe.msgprint("leave_days_current: " + str(leave_days_current))
					if leave_days_current > 0:
						if int(leave_days_current) ==  leave_days_current:
							my_counter = leave_days_current
							for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								# if date in holiday_dates:
								# 	continue

								if my_counter > 0:
									leave_dates.append((date,'session1',"leave type"))
									leave_dates.append((date,'session2',"leave type"))
									my_counter -= 1

								else:
									if dt == self.to_date:       # check for proper variable to match
										leave_dates.append((date,'session1',"lwp"))
									else:
										leave_dates.append((date,'session1',"lwp"))
										leave_dates.append((date,'session2',"lwp"))
						else:
							my_counter = int(leave_days_current) + 1
							for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								if date in holiday_dates:
									continue
								if my_counter > 0:
									if my_counter == 1:
										leave_dates.append((date,"session1","leave type"))  
										leave_dates.append((date,"session2","lwp"))
									else:
										leave_dates.append((date,"session1","leave type"))
										leave_dates.append((date,"session2","leave type"))
									my_counter -=1

								else:
									if str(dt) == str(self.to_date): 
										leave_dates.append((date,'session1',"lwp"))
									else:
										leave_dates.append((date,'session1',"lwp"))
										leave_dates.append((date,'session2',"lwp"))
					else:
						for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								if date in holiday_dates:
									continue
								if str(dt) == str(self.to_date):       # check for proper variable to match
										leave_dates.append((date,'session1',"lwp"))

								else:
									leave_dates.append((date,'session1',"lwp"))
									leave_dates.append((date,'session2',"lwp"))
				else:

					lwp_sessions = self.lwp_count *2
					# frappe.msgprint(str(lwp_sessions))
					leave_sessions = tot_leave_sessions - lwp_sessions
					leave_days_current = leave_sessions/2
					if leave_days_current > 0:
						my_counter = leave_days_current
						for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
							date = dt.strftime("%Y-%m-%d")
							if date in holiday_dates:
									continue
							if  str(dt) == str(self.from_date):      # check for proper variable to match
								# frappe.msgprint(str(dt))
								leave_dates.append((date,"session2","leave_type"))
								my_counter = my_counter - 0.5 
							else:
								if my_counter > 0:
									if int(my_counter) == my_counter:
										leave_dates.append((date,'session1',"leave type"))
										leave_dates.append((date,'session2',"leave type"))
										my_counter -=1
									else:
										if int(my_counter) == 0:
											leave_dates.append((date,'session1',"leave type"))
											leave_dates.append((date,'session2',"lwp"))
										else:
											leave_dates.append((date,'session1',"leave type"))
											leave_dates.append((date,'session2',"leave_type"))
										my_counter -=1

								else:
									leave_dates.append((date,'session1',"lwp"))
									leave_dates.append((date,'session2',"lwp"))

					else:
						for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								if date in holiday_dates:
									continue
								if str(dt) == str(self.from_date):       # check for proper variable to match
										leave_dates.append((date,'session2',"lwp"))

								else:
									leave_dates.append((date,'session1',"lwp"))
									leave_dates.append((date,'session2',"lwp"))
			else:
				lwp_sessions = self.lwp_count *2
				leave_sessions = tot_leave_sessions - lwp_sessions
				leave_days_current = leave_sessions/2
				if leave_days_current > 0:
					if int(leave_days_current) ==  leave_days_current:
						my_counter = leave_days_current
						for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
							date = dt.strftime("%Y-%m-%d")
							if date in holiday_dates:
									continue
							if my_counter > 0:
								leave_dates.append((date,'session1',"leave type"))
								leave_dates.append((date,'session2',"leave type"))
								my_counter -= 1
							else:

								leave_dates.append((date,'session1',"lwp"))
								leave_dates.append((date,'session2',"lwp"))
				
					else:
							my_counter = int(leave_days_current) + 1
							for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
								date = dt.strftime("%Y-%m-%d")
								if date in holiday_dates:
									continue
								if my_counter > 0:
									if my_counter == 1:
										leave_dates.append((date,"session1","leave type"))  
										leave_dates.append((date,"session2","lwp"))
									else:
										leave_dates.append((date,"session1","leave type"))
										leave_dates.append((date,"session2","leave type"))
									my_counter -=1			
								else:
									leave_dates.append((date,'session1',"lwp"))
									leave_dates.append((date,'session2',"lwp"))
				else:
					for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
							date = dt.strftime("%Y-%m-%d")
							if date in holiday_dates:
									continue
							leave_dates.append((date,'session1',"lwp"))
							leave_dates.append((date,'session2',"lwp"))

		for date, session, leave_type in leave_dates:
			if leave_type == 'lwp':
				lwp_dates.append(date)
			else:
				leave_type_dates.append(date)
		unique_lwp_dates_set = set(lwp_dates)
		unique_leave_type_dates_set = set(leave_type_dates)
		unique_lwp_dates = list(unique_lwp_dates_set)
		unique_leave_type_dates = list(unique_leave_type_dates_set)

		return unique_lwp_dates, unique_leave_type_dates
	
	def create_leave_ledger_entry(self, submit=True):
		unique_lwp_dates, unique_leave_type_dates = self.calculate_unique_dates()
		unique_lwp_dates = sorted(unique_lwp_dates)
		unique_leave_type_dates = sorted(unique_leave_type_dates)
		common_date =None
		for date in unique_leave_type_dates:
			if date in unique_leave_type_dates:
				common_date = date	
		if self.status != "Approved" and submit:
			return
		expiry_date = get_allocation_expiry_for_cf_leaves(
			self.employee, self.leave_type, self.to_date, self.from_date
		)
		lwp = frappe.db.get_value("Leave Type", self.leave_type, "is_lwp")
		also_lwp = frappe.db.get_value("Leave Type", 'Leave Without Pay', "is_lwp")
		

		if expiry_date:
			self.create_ledger_entry_for_intermediate_allocation_expiry(expiry_date, submit, lwp)
		else:
			alloc_on_from_date, alloc_on_to_date = self.get_allocation_based_on_application_dates()
			if self.is_separate_ledger_entry_required(alloc_on_from_date, alloc_on_to_date):
				# required only if negative balance is allowed for leave type
				# else will be stopped in validation itself
				self.create_separate_ledger_entries(alloc_on_from_date, alloc_on_to_date, submit, lwp)
			else:
				raise_exception = False if frappe.flags.in_patch else True
				if self.current_leave_type_count > 0:
						args = dict(
							leaves=self.current_leave_type_count * -1,
							from_date=unique_leave_type_dates[0],
							to_date=unique_leave_type_dates[-1],
							is_lwp=lwp,
							session_date=common_date,
							if_half_day = self.half_day_date ,
							holiday_list=get_holiday_list_for_employee(self.employee, raise_exception=raise_exception)
							or "",
						)
						create_leave_ledger_entry(self, args, submit)
				if self.lwp_count > 0:
						args = dict(
							leaves=self.lwp_count * -1,
							from_date=unique_lwp_dates[0],
							to_date=unique_lwp_dates[-1],
							leave_type = 'Leave Without Pay',
							is_lwp=also_lwp,
							session_date=common_date,
							if_half_day = self.half_day_date ,
							holiday_list=get_holiday_list_for_employee(self.employee, raise_exception=raise_exception)
							or "",
						)
						create_leave_ledger_entry(self, args, submit)
	def is_separate_ledger_entry_required(
		self, alloc_on_from_date: Optional[Dict] = None, alloc_on_to_date: Optional[Dict] = None
	) -> bool:
		"""Checks if application dates fall in separate allocations"""
		if (
			(alloc_on_from_date and not alloc_on_to_date)
			or (not alloc_on_from_date and alloc_on_to_date)
			or (
				alloc_on_from_date and alloc_on_to_date and alloc_on_from_date.name != alloc_on_to_date.name
			)
		):
			return True
		return False

	def create_separate_ledger_entries(self, alloc_on_from_date, alloc_on_to_date, submit, lwp):
		"""Creates separate ledger entries for application period falling into separate allocations"""
		# for creating separate ledger entries existing allocation periods should be consecutive
		if (
			submit
			and alloc_on_from_date
			and alloc_on_to_date
			and add_days(alloc_on_from_date.to_date, 1) != alloc_on_to_date.from_date
		):
			frappe.throw(
				_(
					"Leave Application period cannot be across two non-consecutive leave allocations {0} and {1}."
				).format(
					get_link_to_form("Leave Allocation", alloc_on_from_date.name),
					get_link_to_form("Leave Allocation", alloc_on_to_date),
				)
			)

		raise_exception = False if frappe.flags.in_patch else True

		if alloc_on_from_date:
			first_alloc_end = alloc_on_from_date.to_date
			second_alloc_start = add_days(alloc_on_from_date.to_date, 1)
		else:
			first_alloc_end = add_days(alloc_on_to_date.from_date, -1)
			second_alloc_start = alloc_on_to_date.from_date

		leaves_in_first_alloc = get_number_of_leave_days(
			self.employee,
			self.leave_type,
			self.from_date,
			first_alloc_end,
			self.half_day,
			self.half_day_date,
		)
		leaves_in_second_alloc = get_number_of_leave_days(
			self.employee,
			self.leave_type,
			second_alloc_start,
			self.to_date,
			self.half_day,
			self.half_day_date,
		)

		args = dict(
			is_lwp=lwp,
			holiday_list=get_holiday_list_for_employee(self.employee, raise_exception=raise_exception)
			or "",
		)

		if leaves_in_first_alloc:
			args.update(
				dict(from_date=self.from_date, to_date=first_alloc_end, leaves=leaves_in_first_alloc * -1)
			)
			create_leave_ledger_entry(self, args, submit)

		if leaves_in_second_alloc:
			args.update(
				dict(from_date=second_alloc_start, to_date=self.to_date, leaves=leaves_in_second_alloc * -1)
			)
			create_leave_ledger_entry(self, args, submit)

	def create_ledger_entry_for_intermediate_allocation_expiry(self, expiry_date, submit, lwp):
		"""Splits leave application into two ledger entries to consider expiry of allocation"""
		raise_exception = False if frappe.flags.in_patch else True

		leaves = get_number_of_leave_days(
			self.employee, self.leave_type, self.from_date, expiry_date, self.half_day, self.half_day_date
		)

		if leaves:
			args = dict(
				from_date=self.from_date,
				to_date=expiry_date,
				leaves=leaves * -1,
				is_lwp=lwp,
				holiday_list=get_holiday_list_for_employee(self.employee, raise_exception=raise_exception)
				or "",
			)
			create_leave_ledger_entry(self, args, submit)

		if getdate(expiry_date) != getdate(self.to_date):
			start_date = add_days(expiry_date, 1)
			leaves = get_number_of_leave_days(
				self.employee, self.leave_type, start_date, self.to_date, self.half_day, self.half_day_date
			)

			if leaves:
				args.update(dict(from_date=start_date, to_date=self.to_date, leaves=leaves * -1))
				create_leave_ledger_entry(self, args, submit)


def get_allocation_expiry_for_cf_leaves(
	employee: str, leave_type: str, to_date: str, from_date: str
) -> str:
	"""Returns expiry of carry forward allocation in leave ledger entry"""
	expiry = frappe.get_all(
		"Leave Ledger Entry",
		filters={
			"employee": employee,
			"leave_type": leave_type,
			"is_carry_forward": 1,
			"transaction_type": "Leave Allocation",
			"to_date": ["between", (from_date, to_date)],
			"docstatus": 1,
		},
		fields=["to_date"],
	)
	return expiry[0]["to_date"] if expiry else ""
# def find_common_dates_with_condition(self):
#     unique_lwp_dates, unique_leave_type_dates = self.calculate_unique_dates()
#     common_date = None
#     frappe.msgprint('++++++++++++'+str(common_date)) 
#     for date in unique_lwp_dates:
#         if date in unique_leave_type_dates:
#             common_date = date
#             break 
#     return common_date


@frappe.whitelist()
def number_of_leave_days(
	
	employee: str,
	leave_type: str,
	from_date: str,
	to_date: str,
	half_day: Optional[int] = None,
	half_day_date: Optional[str] = None,
	# holiday_list: Optional[str] = None,
) -> float:
	"""Returns number of leave days between 2 dates after considering half day and holidays
	(Based on the include_holiday setting in Leave Type)"""
	if cint(half_day) == 1:
		if getdate(from_date) == getdate(to_date):
			number_of_days = 0.5
		elif half_day_date and getdate(from_date) <= getdate(half_day_date) <= getdate(to_date):
			number_of_days = date_diff(to_date, from_date) + 0.5
		else:
			number_of_days = date_diff(to_date, from_date) + 1

	else:
		number_of_days = date_diff(to_date, from_date) + 1

	#----------------------------------------------------------------------------------------
	employee_holiday = []
	employee_holiday = get_employee_holidays(employee, from_date, to_date)
	filtered_holidays = []
	for holiday in employee_holiday:
		date = holiday['holiday_date']
		weekly_off = holiday['weekly_off']
		filtered_holidays.append([date, {'weekly_off': weekly_off}])
	from_date_is_wo = False
	to_date_is_wo = False
	leave_days = 0
	for dt in daterange(getdate(from_date), getdate(to_date)):
		date = dt.strftime("%Y-%m-%d")
		should_continue = False
		weekly_off = False
		
		for holiday in filtered_holidays:
			holiday_date, weekly_off_info = holiday
			if to_date == holiday_date.strftime("%Y-%m-%d"):
				# frappe.msgprint("weekly_off"+str(weekly_off_info))
				if weekly_off_info.get('weekly_off') == 1:
					to_date_is_wo = True
			if date == holiday_date.strftime("%Y-%m-%d"):
				# frappe.msgprint("#########"+str(date))
				should_continue = True
				if weekly_off_info.get('weekly_off') == 1:
					weekly_off = True
					should_continue = False
				break
		if date == from_date and weekly_off == True:
			should_continue =True
			from_date_is_wo = True
		elif date == (getdate(from_date) + timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off  and from_date_is_wo :
			
			should_continue =True
		elif date == to_date and weekly_off:
			should_continue = True
		elif date == (getdate(to_date) - timedelta(days=1)).strftime("%Y-%m-%d") and weekly_off and to_date_is_wo:
			should_continue = True
		if should_continue == True:
			leave_days +=1

#--------------------------------------------------------------------------------------------------------------------
	
	number_of_days = flt(number_of_days) - flt(leave_days)
	
		
		
	return number_of_days

@frappe.whitelist()
def get_number_of_leave_days(
	employee: str,
	leave_type: str,
	from_date: str,
	to_date: str,
	half_day: Optional[int] = None,
	half_day_date: Optional[str] = None,
	holiday_list: Optional[str] = None,
) -> float:
	"""Returns number of leave days between 2 dates after considering half day and holidays
	(Based on the include_holiday setting in Leave Type)"""
	if cint(half_day) == 1:
		if getdate(from_date) == getdate(to_date):
			number_of_days = 0.5
		elif half_day_date and getdate(from_date) <= getdate(half_day_date) <= getdate(to_date):
			number_of_days = date_diff(to_date, from_date) + 0.5
		else:
			number_of_days = date_diff(to_date, from_date) + 1

	else:
		number_of_days = date_diff(to_date, from_date) + 1

	if not frappe.db.get_value("Leave Type", leave_type, "include_holiday"):
		number_of_days = flt(number_of_days) - flt(
			get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
		)
		
		
	return number_of_days


@frappe.whitelist()
def get_leave_details(employee, date, to_date):
    from datetime import datetime 
    from dateutil.relativedelta import relativedelta
    
    from_date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()

    from_date_month_start = from_date_obj.replace(day=1)
    to_date_month_end = from_date_month_start + relativedelta(day=31)

    allocation_records = get_leave_allocation_records(employee, date)
    leave_allocation = {}
    total_leaves_allocated = sum(allocation['total_leaves_allocated'] for allocation in allocation_records.values())

    # Calculate monthly allocation value
    monthly_allocation = calculate_monthly_allocation(total_leaves_allocated, from_date_obj, to_date_obj)
    allocation_value = next(iter(monthly_allocation.values()))

    total_monthly_taken_leaves_positive = 0
    total_now_taken_leave_positive = 0

    for d in allocation_records:
        allocation = allocation_records[d]
        remaining_leaves = get_leave_balance_on(
            employee, d, date, to_date=allocation.to_date, consider_all_leaves_in_the_allocation_period=True
        )
	

        end_date = allocation.to_date
        leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, end_date) * -1
        monthly_taken_leaves = get_leaves_for_period(employee, d, from_date_month_start, to_date_month_end)
        now_taken_leave = get_leaves_for_period(employee, d, allocation.from_date, end_date)
        now_taken_leave_positive = abs(now_taken_leave)
        total_now_taken_leave_positive += now_taken_leave_positive 

        leaves_pending = get_leaves_pending_approval_for_period(
            employee, d, allocation.from_date, end_date
        )
        expired_leaves = allocation.total_leaves_allocated - (remaining_leaves + leaves_taken)
	

        leave_allocation[d] = {
            "total_leaves": allocation.total_leaves_allocated,
            "expired_leaves": max(0, expired_leaves),
            "leaves_taken": leaves_taken,
            "monthly_taken_leaves": monthly_taken_leaves,
            "leaves_pending_approval": leaves_pending,
            "remaining_leaves": remaining_leaves,
        }
    
    balance = allocation_value * from_date_obj.month
    total_available = balance - total_now_taken_leave_positive

    lwp = frappe.get_list("Leave Type", filters={"is_lwp": 1}, pluck="name")
    
    return {
        "leave_allocation": leave_allocation,
        "leave_approver": get_leave_approver(employee),
        "lwps": lwp,
        "total_now_taken_leave_positive": total_now_taken_leave_positive,
        "balance": balance,
        "allocation_value": allocation_value,
        "total_available": total_available,
    }


from dateutil.relativedelta import relativedelta

def calculate_monthly_allocation(total_leaves_allocated, from_date_obj, to_date_obj):
    # Calculate the number of months between from_date and to_date
    months_between = (to_date_obj.year - from_date_obj.year) * 12 + to_date_obj.month - from_date_obj.month + 1
    
    # Calculate monthly leave allocation
    monthly_allocation = total_leaves_allocated / 12
    
    # Create a dictionary to store monthly allocations
    monthly_allocations = {}
    
    
    current_month = from_date_obj.month
    current_year = from_date_obj.year
    
    for _ in range(months_between):
        if current_month > 12:
            current_month = 1
            current_year += 1
        
        month_year_key = f"{current_year}-{current_month:02d}"
        monthly_allocations[month_year_key] = monthly_allocation
        
        current_month += 1
    
    return monthly_allocations

@frappe.whitelist()
def get_leave_balance_on(
	employee: str,
	leave_type: str,
	date: str,
	to_date: str = None,
	consider_all_leaves_in_the_allocation_period: bool = False,
	for_consumption: bool = False,
):
	"""
	Returns leave balance till date
	:param employee: employee name
	:param leave_type: leave type
	:param date: date to check balance on
	:param to_date: future date to check for allocation expiry
	:param consider_all_leaves_in_the_allocation_period: consider all leaves taken till the allocation end date
	:param for_consumption: flag to check if leave balance is required for consumption or display
	        eg: employee has leave balance = 10 but allocation is expiring in 1 day so employee can only consume 1 leave
	        in this case leave_balance = 10 but leave_balance_for_consumption = 1
	        if True, returns a dict eg: {'leave_balance': 10, 'leave_balance_for_consumption': 1}
	        else, returns leave_balance (in this case 10)
	"""

	if not to_date:
		to_date = nowdate()

	allocation_records = get_leave_allocation_records(employee, date, leave_type)
	allocation = allocation_records.get(leave_type, frappe._dict())

	end_date = allocation.to_date if cint(consider_all_leaves_in_the_allocation_period) else date
	cf_expiry = get_allocation_expiry_for_cf_leaves(employee, leave_type, to_date, date)

	leaves_taken = get_leaves_for_period(employee, leave_type, allocation.from_date, end_date)
	

	remaining_leaves = get_remaining_leaves(allocation, leaves_taken, date, cf_expiry)
	# frappe.msgprint('hello:' + str(remaining_leaves))

	if for_consumption:
		return remaining_leaves
	else:
		return remaining_leaves.get("leave_balance")



def get_leave_allocation_records(employee, date, leave_type=None):
	"""Returns the total allocated leaves and carry forwarded leaves based on ledger entries"""
	Ledger = frappe.qb.DocType("Leave Ledger Entry")

	cf_leave_case = (
		frappe.qb.terms.Case().when(Ledger.is_carry_forward == "1", Ledger.leaves).else_(0)
	)
	sum_cf_leaves = Sum(cf_leave_case).as_("cf_leaves")

	new_leaves_case = (
		frappe.qb.terms.Case().when(Ledger.is_carry_forward == "0", Ledger.leaves).else_(0)
	)
	sum_new_leaves = Sum(new_leaves_case).as_("new_leaves")

	query = (
		frappe.qb.from_(Ledger)
		.select(
			sum_cf_leaves,
			sum_new_leaves,
			Min(Ledger.from_date).as_("from_date"),
			Max(Ledger.to_date).as_("to_date"),
			Ledger.leave_type,
		)
		.where(
			(Ledger.from_date <= date)
			& (Ledger.to_date >= date)
			& (Ledger.docstatus == 1)
			& (Ledger.transaction_type == "Leave Allocation")
			& (Ledger.employee == employee)
			& (Ledger.is_expired == 0)
			& (Ledger.is_lwp == 0)
		)
	)

	if leave_type:
		query = query.where((Ledger.leave_type == leave_type))
	query = query.groupby(Ledger.employee, Ledger.leave_type)

	allocation_details = query.run(as_dict=True)

	allocated_leaves = frappe._dict()
	for d in allocation_details:
		allocated_leaves.setdefault(
			d.leave_type,
			frappe._dict(
				{
					"from_date": d.from_date,
					"to_date": d.to_date,
					"total_leaves_allocated": flt(d.cf_leaves) + flt(d.new_leaves),
					"unused_leaves": d.cf_leaves,
					"new_leaves_allocated": d.new_leaves,
					"leave_type": d.leave_type,
				}
			),
		)
	return allocated_leaves


def get_leaves_pending_approval_for_period(
	employee: str, leave_type: str, from_date: str, to_date: str
) -> float:
	"""Returns leaves that are pending for approval"""
	leaves = frappe.get_all(
		"Leave Application",
		filters={"employee": employee, "leave_type": leave_type, "status": "Open"},
		or_filters={
			"from_date": ["between", (from_date, to_date)],
			"to_date": ["between", (from_date, to_date)],
		},
		fields=["SUM(current_leave_type_count) as leaves"],
	)[0]
	return leaves["leaves"] if leaves["leaves"] else 0.0


def get_remaining_leaves(
	allocation: Dict, leaves_taken: float, date: str, cf_expiry: str
) -> Dict[str, float]:
	"""Returns a dict of leave_balance and leave_balance_for_consumption
	leave_balance returns the available leave balance
	leave_balance_for_consumption returns the minimum leaves remaining after comparing with remaining days for allocation expiry
	"""

	def _get_remaining_leaves(remaining_leaves, end_date):
		"""Returns minimum leaves remaining after comparing with remaining days for allocation expiry"""
		if remaining_leaves > 0:
			remaining_days = date_diff(end_date, date) + 1
			remaining_leaves = min(remaining_days, remaining_leaves)

		return remaining_leaves

	leave_balance = leave_balance_for_consumption = flt(allocation.total_leaves_allocated) + flt(
		leaves_taken
	)

	# balance for carry forwarded leaves
	if cf_expiry and allocation.unused_leaves:
		cf_leaves = flt(allocation.unused_leaves) + flt(leaves_taken)
		remaining_cf_leaves = _get_remaining_leaves(cf_leaves, cf_expiry)

		leave_balance = flt(allocation.new_leaves_allocated) + flt(cf_leaves)
		leave_balance_for_consumption = flt(allocation.new_leaves_allocated) + flt(remaining_cf_leaves)

	remaining_leaves = _get_remaining_leaves(leave_balance_for_consumption, allocation.to_date)
	return frappe._dict(leave_balance=leave_balance, leave_balance_for_consumption=remaining_leaves)


def get_leaves_for_period(
	employee: str, leave_type: str, from_date: str, to_date: str, skip_expired_leaves: bool = True
) -> float:
	leave_entries = get_leave_entries(employee, leave_type, from_date, to_date)
	leave_days = 0

	for leave_entry in leave_entries:
		inclusive_period = leave_entry.from_date >= getdate(
			from_date
		) and leave_entry.to_date <= getdate(to_date)

		if inclusive_period and leave_entry.transaction_type == "Leave Encashment":
			leave_days += leave_entry.leaves

		elif (
			inclusive_period
			and leave_entry.transaction_type == "Leave Allocation"
			and leave_entry.is_expired
			and not skip_expired_leaves
		):
			leave_days += leave_entry.leaves

		elif leave_entry.transaction_type == "Leave Application":
			if leave_entry.from_date < getdate(from_date):
				leave_entry.from_date = from_date
			if leave_entry.to_date > getdate(to_date):
				leave_entry.to_date = to_date

			# half_day = 0
			# half_day_date = None
			# # fetch half day date for leaves with half days
			# if leave_entry.leaves % 1 or leave_entry.session_date:
			# 	half_day = 1
			# 	half_day_date = frappe.db.get_value(
			# 		"Leave Application", {"name": leave_entry.transaction_name}, ["half_day_date"]
			# 	)
			# 	session_date = leave_entry.session_date
			# 	frappe.msgprint("session date:"+str(session_date))
			# 	# half_day_date =leave_entry.if_half_day
				
				
				
			leave_days += (
				leave_entry.leaves
			
			)
		
			
	

	return leave_days
def calculate_leave_days(
	employee: str,
	leave_type: str,
	from_date: str,
	to_date: str,
	half_day: Optional[int] = None,
	half_day_date: Optional[str] = None,
	session_date: Optional[str] = None,
	holiday_list: Optional[str] = None,
) -> float:
	"""Returns number of leave days between 2 dates after considering half day and holidays
	(Based on the include_holiday setting in Leave Type)"""
	if cint(half_day) == 1:
		if getdate(from_date) == getdate(to_date):
			number_of_days = 0.5
		elif half_day_date and getdate(from_date) <= getdate(half_day_date) <= getdate(to_date):
			number_of_days = date_diff(to_date, from_date) + 0.5
		elif session_date and getdate(from_date) <= getdate(session_date) <= getdate(to_date):
			number_of_days = date_diff(to_date, from_date) + 0.5
		else:
			number_of_days = date_diff(to_date, from_date) + 1

		
		

	else:
		number_of_days = date_diff(to_date, from_date) + 1
	# if session_date and getdate(from_date) <= getdate(session_date) <= getdate(to_date):
	# 	number_of_days -= 0.5

	if not frappe.db.get_value("Leave Type", leave_type, "include_holiday"):
		number_of_days = flt(number_of_days) - flt(
			get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
		)
		
		
		
	return number_of_days


def get_leave_entries(employee, leave_type, from_date, to_date ):
	"""Returns leave entries between from_date and to_date."""
	return frappe.db.sql(
		"""
		SELECT
			employee, leave_type, from_date, to_date, leaves, transaction_name, session_date, if_half_day, transaction_type, holiday_list,
			is_carry_forward, is_expired
		FROM `tabLeave Ledger Entry`
		WHERE employee=%(employee)s AND leave_type=%(leave_type)s
			AND docstatus=1
			AND (leaves<0
				OR is_expired=1)
			AND (from_date between %(from_date)s AND %(to_date)s
				OR to_date between %(from_date)s AND %(to_date)s
				OR (from_date < %(from_date)s AND to_date > %(to_date)s))
	""",
		{"from_date": from_date, "to_date": to_date, "employee": employee, "leave_type": leave_type},
		as_dict=1,
	)


@frappe.whitelist()
def get_holidays(employee, from_date, to_date, holiday_list=None):
	"""get holidays between two dates for the given employee"""
	if not holiday_list:
		holiday_list = get_holiday_list_for_employee(employee)

	holidays = frappe.db.sql(
		"""select count(distinct holiday_date) from `tabHoliday` h1, `tabHoliday List` h2
		where h1.parent = h2.name and h1.holiday_date between %s and %s
		and h2.name = %s""",
		(from_date, to_date, holiday_list),
	)[0][0]
	# frappe.msgprint(str(holiday_list))
	return holidays


def is_lwp(leave_type):
	lwp = frappe.db.sql("select is_lwp from `tabLeave Type` where name = %s", leave_type)
	return lwp and cint(lwp[0][0]) or 0


@frappe.whitelist()
def get_events(start, end, filters=None):
	from frappe.desk.reportview import get_filters_cond

	events = []

	employee = frappe.db.get_value(
		"Employee", filters={"user_id": frappe.session.user}, fieldname=["name", "company"], as_dict=True
	)

	if employee:
		employee, company = employee.name, employee.company
	else:
		employee = ""
		company = frappe.db.get_value("Global Defaults", None, "default_company")

	conditions = get_filters_cond("Leave Application", filters, [])
	# show department leaves for employee
	if "Employee" in frappe.get_roles():
		add_department_leaves(events, start, end, employee, company)

	add_leaves(events, start, end, conditions)
	add_block_dates(events, start, end, employee, company)
	add_holidays(events, start, end, employee, company)

	return events


def add_department_leaves(events, start, end, employee, company):
	department = frappe.db.get_value("Employee", employee, "department")

	if not department:
		return

	# department leaves
	department_employees = frappe.db.sql_list(
		"""select name from tabEmployee where department=%s
		and company=%s""",
		(department, company),
	)

	filter_conditions = ' and employee in ("%s")' % '", "'.join(department_employees)
	add_leaves(events, start, end, filter_conditions=filter_conditions)


def add_leaves(events, start, end, filter_conditions=None):
	from frappe.desk.reportview import build_match_conditions

	conditions = []

	if not cint(
		frappe.db.get_value("HR Settings", None, "show_leaves_of_all_department_members_in_calendar")
	):
		match_conditions = build_match_conditions("Leave Application")

		if match_conditions:
			conditions.append(match_conditions)

	query = """SELECT
		docstatus,
		name,
		employee,
		employee_name,
		leave_type,
		from_date,
		to_date,
		half_day,
		status,
		color
	FROM `tabLeave Application`
	WHERE
		from_date <= %(end)s AND to_date >= %(start)s <= to_date
		AND docstatus < 2
		AND status in ('Approved', 'Open')
	"""

	if conditions:
		query += " AND " + " AND ".join(conditions)

	if filter_conditions:
		query += filter_conditions

	for d in frappe.db.sql(query, {"start": start, "end": end}, as_dict=True):
		e = {
			"name": d.name,
			"doctype": "Leave Application",
			"from_date": d.from_date,
			"to_date": d.to_date,
			"docstatus": d.docstatus,
			"color": d.color,
			"all_day": int(not d.half_day),
			"title": cstr(d.employee_name)
			+ f" ({cstr(d.leave_type)})"
			+ (" " + _("(Half Day)") if d.half_day else ""),
		}
		if e not in events:
			events.append(e)


def add_block_dates(events, start, end, employee, company):
	# block days
	from erpnext.hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates

	cnt = 0
	block_dates = get_applicable_block_dates(start, end, employee, company, all_lists=True)

	for block_date in block_dates:
		events.append(
			{
				"doctype": "Leave Block List Date",
				"from_date": block_date.block_date,
				"to_date": block_date.block_date,
				"title": _("Leave Blocked") + ": " + block_date.reason,
				"name": "_" + str(cnt),
			}
		)
		cnt += 1


def add_holidays(events, start, end, employee, company):
	applicable_holiday_list = get_holiday_list_for_employee(employee, company)
	if not applicable_holiday_list:
		return

	for holiday in frappe.db.sql(
		"""select name, holiday_date, description
		from `tabHoliday` where parent=%s and holiday_date between %s and %s""",
		(applicable_holiday_list, start, end),
		as_dict=True,
	):
		events.append(
			{
				"doctype": "Holiday",
				"from_date": holiday.holiday_date,
				"to_date": holiday.holiday_date,
				"title": _("Holiday") + ": " + cstr(holiday.description),
				"name": holiday.name,
			}
		)


@frappe.whitelist()
def get_mandatory_approval(doctype):
	mandatory = ""
	if doctype == "Leave Application":
		mandatory = frappe.db.get_single_value(
			"HR Settings", "leave_approver_mandatory_in_leave_application"
		)
	else:
		mandatory = frappe.db.get_single_value(
			"HR Settings", "expense_approver_mandatory_in_expense_claim"
		)

	return mandatory


def get_approved_leaves_for_period(employee, leave_type, from_date, to_date):
	LeaveApplication = frappe.qb.DocType("Leave Application")
	query = (
		frappe.qb.from_(LeaveApplication)
		.select(
			LeaveApplication.employee,
			LeaveApplication.leave_type,
			LeaveApplication.from_date,
			LeaveApplication.to_date,
			LeaveApplication.total_leave_days,
		)
		.where(
			(LeaveApplication.employee == employee)
			& (LeaveApplication.docstatus == 1)
			& (LeaveApplication.status == "Approved")
			& (
				(LeaveApplication.from_date.between(from_date, to_date))
				| (LeaveApplication.to_date.between(from_date, to_date))
				| ((LeaveApplication.from_date < from_date) & (LeaveApplication.to_date > to_date))
			)
		)
	)

	if leave_type:
		query = query.where(LeaveApplication.leave_type == leave_type)
	leave_applications = query.run(as_dict=True)

	leave_days = 0
	for leave_app in leave_applications:
		if leave_app.from_date >= getdate(from_date) and leave_app.to_date <= getdate(to_date):
			leave_days += leave_app.total_leave_days
		else:
			if leave_app.from_date < getdate(from_date):
				leave_app.from_date = from_date
			if leave_app.to_date > getdate(to_date):
				leave_app.to_date = to_date

			leave_days += get_number_of_leave_days(
				employee, leave_type, leave_app.from_date, leave_app.to_date
			)

	return leave_days


@frappe.whitelist()
def get_leave_approver(employee):
	leave_approver, department = frappe.db.get_value(
		"Employee", employee, ["leave_approver", "department"]
	)

	if not leave_approver and department:
		leave_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "leave_approvers", "idx": 1},
			"approver",
		)

	return leave_approver