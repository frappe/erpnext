# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.utils.email_lib import sendmail
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

sql = webnotes.conn.sql
set = webnotes.conn.set
get_value = webnotes.conn.get_value

# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def get_project_details(self):
		cust = sql("select customer, customer_name from `tabProject` where name = %s", self.doc.project)
		if cust:
			ret = {'customer': cust and cust[0][0] or '', 'customer_name': cust and cust[0][1] or ''}
			return ret
	
	def get_customer_details(self):
		cust = sql("select customer_name from `tabCustomer` where name=%s", self.doc.customer)
		if cust:
			ret = {'customer_name': cust and cust[0][0] or ''}
			return ret
	
	def get_allocated_to_name(self):
		as_em = sql("select first_name, last_name from `tabProfile` where name=%s",str(self.doc.allocated_to))
		ret = { 'allocated_to_name' : as_em and (as_em[0][0] + ' ' + as_em[0][1]) or ''}
		return ret

	# validate
	#--------------------------------------------	 


	def validate(self):
		if not self.doc.opening_date:
			msgprint("Please enter Opening Date.")
			raise Exception
		elif getdate(self.doc.opening_date) > getdate(nowdate()):
			msgprint("Opening date can not be future date")
			raise Exception
		
		if self.doc.exp_start_date and self.doc.exp_end_date and getdate(self.doc.exp_start_date) > getdate(self.doc.exp_end_date):
			msgprint("'Expected Start Date' can not be greater than 'Expected End Date'")
			raise Exception
		
		if self.doc.act_start_date and self.doc.act_end_date and getdate(self.doc.act_start_date) > getdate(self.doc.act_end_date):
			msgprint("'Actual Start Date' can not be greater than 'Actual End Date'")
			raise Exception
		
		if self.doc.opening_date and self.doc.review_date and getdate(self.doc.opening_date) > getdate(self.doc.review_date):
			msgprint("Review Date should be greater than or equal to Opening Date ")
			raise Exception
		
		if self.doc.closing_date and self.doc.review_date and getdate(self.doc.closing_date) < getdate(self.doc.review_date):
			msgprint("Closing Date should be greater than or equal to Review Date ")
			raise Exception

	# on update
	#--------------------------------------------	 
	
	def on_update(self):
		if self.doc.status =='Open' and self.doc.allocated_to:
			if self.doc.task_email_notify==1:
				if (self.doc.allocated_to == self.doc.allocated_to_old):
					return			 		
				else:
					self.doc.allocated_to_old = self.doc.allocated_to
					self.sent_notification()
			if self.doc.exp_start_date:
				sql("delete from tabEvent where ref_type='Task' and ref_name=%s", self.doc.name)
				self.add_calendar_event()
			else:
				msgprint("An Expeted start date has not been set for this task.Please set a, 'Expected Start date'\
				to add an event to allocated persons calender.You can save a task without this also.")
			pass	
	
	def validate_for_pending_review(self):
		if not self.doc.allocated_to:
			msgprint("Please enter allocated_to.")
			raise Exception
		self.validate_with_timesheet_dates()
	#Sent Notification
	def sent_notification(self):
		msg2="""This is an auto generated email.<br/>A task %s has been assigned to you by %s on %s<br/><br/>\
		Project: %s <br/><br/>Review Date: %s<br/><br/>Closing Date: %s <br/><br/>Details: %s <br/><br/>""" \
		%(self.doc.name, self.doc.senders_name, self.doc.opening_date, \
		self.doc.project, self.doc.review_date, self.doc.closing_date, self.doc.description)
		sendmail(self.doc.allocated_to, sender='automail@webnotestech.com', msg=msg2,send_now=1,\
		subject='A task has been assigned')
		self.doc.sent_reminder=0
	
	#validate before closing task
	def validate_for_closed(self):
		self.check_non_submitted_timesheets()
		self.get_actual_total_hrs()
	
	def check_non_submitted_timesheets(self):
		chk = sql("select t1.name from `tabTimesheet` t1, `tabTimesheet Detail` t2 where t2.parent=t1.name and t2.task_id=%s and t1.status='Draft'", self.doc.name)
		if chk:
			chk_lst = [x[0] for x in chk]
			msgprint("Please submit timesheet(s) : "+','.join(chk_lst)+" before declaring this task as completed. As details of this task present in timesheet(s)")
			raise Exception
	
	#calculate actual total hours taken to complete task from timesheets
	def get_actual_total_hrs(self):
		import datetime
		import time
		chk = sql("select t2.act_total_hrs from `tabTimesheet` t1, `tabTimesheet Detail` t2 where t2.parent = t1.name and t2.task_id = %s and t1.status = 'Submitted' and ifnull(t2.act_total_hrs, '')!='' order by t1.timesheet_date asc", self.doc.name)
		if chk:
			chk_lst = [x[0] for x in chk]
			actual_total = total =0
			
			for m in chk_lst:
				m1, m2=[], 0
				m1 = m.split(":")
				m2 = (datetime.timedelta(minutes=cint(m1[1]), hours=cint(m1[0]))).seconds
				total = total + m2
			
			actual_total = time.strftime("%H:%M", time.gmtime(total))
			set(self.doc, 'act_total_hrs', actual_total)
	
	# validate and fetch actual start and end date
	def validate_with_timesheet_dates(self):
		chk = sql("select t1.name, t1.timesheet_date from `tabTimesheet` t1, `tabTimesheet Detail` t2 where t2.parent = t1.name and t2.task_id = %s and t1.status = 'Submitted' order by t1.timesheet_date asc", self.doc.name, as_dict=1)
		if chk:
			if self.doc.act_start_date:
				if chk[0]['timesheet_date'] > getdate(self.doc.act_start_date) or chk[0]['timesheet_date'] < getdate(self.doc.act_start_date):
					msgprint("Actual start date of this task is "+cstr(chk[0]['timesheet_date'])+" as per timesheet "+cstr(chk[0]['name']))
					raise Exception
			else:
				self.doc.act_start_date = chk[0]['timesheet_date']
			
			if self.doc.act_end_date:
				if chk[len(chk)-1]['timesheet_date'] < getdate(self.doc.act_end_date) or chk[len(chk)-1]['timesheet_date'] > getdate(self.doc.act_end_date):
					msgprint("Actual end date of this task is "+cstr(chk[len(chk)-1]['timesheet_date'])+" as per timesheet "+cstr(chk[len(chk)-1]['name']))
					raise Exception
			else:
				self.doc.act_end_date = chk[len(chk)-1]['timesheet_date']
	
	def set_for_review(self):
		self.check_non_submitted_timesheets()
		self.validate_for_pending_review()
		self.get_actual_total_hrs()
		self.doc.review_date = nowdate()
		set(self.doc, 'status', 'Pending Review')
		self.doc.save()
		return cstr('true')
	
	def reopen_task(self):
		set(self.doc, 'status', 'Open')
		self.doc.save()
		return cstr('true')
	
	def declare_completed(self):
		if self.doc.status == 'Open':
			self.validate_for_pending_review()
			self.doc.review_date = nowdate()
		else:
			self.validate_with_timesheet_dates()
		self.validate_for_closed()
		self.doc.closing_date = nowdate()
		set(self.doc, 'status', 'Closed')
		self.remove_event_from_calender()
		set(self.doc, 'docstatus', 1)
		self.doc.save()
		return cstr('true')
	def remove_event_from_calender():
		sql("delete from tabEvent where ref_type='Task' and ref_name=%s", self.doc.name)
		self.doc.save()
	def cancel_task(self):
		chk = sql("select distinct t1.name from `tabTimesheet` t1, `tabTimesheet Detail` t2 where t2.parent = t1.name and t2.task_id = %s and t1.status!='Cancelled'", self.doc.name)
		if chk:
			chk_lst = [x[0] for x in chk]
			msgprint("Timesheet(s) "+','.join(chk_lst)+" created against this task. Thus can not be cancelled")
			raise Exception
		else:
			set(self.doc, 'status', 'Cancelled')
			set(self.doc, 'docstatus', 2)
		self.doc.save()
		return cstr('true')

	
	def add_calendar_event(self):
		in_calendar_of = self.doc.allocated_to
		event = Document('Event')
		event.owner = in_calendar_of
		event.description ='' 
		event.event_date = self.doc.exp_start_date and self.doc.exp_start_date or ''
		event.event_hour = '10:00'
		event.event_type = 'Private'
		event.ref_type = 'Task'
		event.ref_name = self.doc.name
		event.save(1)

