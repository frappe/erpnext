# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, cstr, getdate
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes import msgprint, throw, _
from erpnext.utilities.transaction_base import TransactionBase, delete_events

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def get_item_details(self, item_code):
		item = webnotes.conn.sql("""select item_name, description from `tabItem` 
			where name=%s""", (item_code), as_dict=1)
		ret = {
			'item_name': item and item[0]['item_name'] or '',
			'description' : item and item[0]['description'] or ''
		}
		return ret
		
	def generate_schedule(self):
		self.doclist = self.doc.clear_table(self.doclist, 'maintenance_schedule_detail')
		webnotes.conn.sql("""delete from `tabMaintenance Schedule Detail` 
			where parent=%s""", (self.doc.name))
		count = 1
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			self.validate_maintenance_detail()
			s_list = []
			s_list = self.create_schedule_list(d.start_date, d.end_date, d.no_of_visits, d.sales_person)
			for i in range(d.no_of_visits):
				child = addchild(self.doc, 'maintenance_schedule_detail',
					'Maintenance Schedule Detail', self.doclist)
				child.item_code = d.item_code
				child.item_name = d.item_name
				child.scheduled_date = s_list[i].strftime('%Y-%m-%d')
				if d.serial_no:
					child.serial_no = d.serial_no
				child.idx = count
				count = count + 1
				child.sales_person = d.sales_person
				child.save(1)
				
		self.on_update()

	def on_submit(self):
		if not getlist(self.doclist, 'maintenance_schedule_detail'):
			throw("Please click on 'Generate Schedule' to get schedule")
		self.check_serial_no_added()
		self.validate_serial_no_warranty()
		self.validate_schedule()

		email_map = {}
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			if d.serial_no:
				self.update_amc_date(d.serial_no, d.end_date)

			if d.sales_person not in email_map:
				sp = webnotes.bean("Sales Person", d.sales_person).make_controller()
				email_map[d.sales_person] = sp.get_email_id()

			scheduled_date = webnotes.conn.sql("""select scheduled_date from 
				`tabMaintenance Schedule Detail` where sales_person=%s and item_code=%s and 
				parent=%s""", (d.sales_person, d.item_code, self.doc.name), as_dict=1)

			for key in scheduled_date:
				if email_map[d.sales_person]:
					description = "Reference: %s, Item Code: %s and Customer: %s" % \
						(self.doc.name, d.item_code, self.doc.customer)
					webnotes.bean({
						"doctype": "Event",
						"owner": email_map[d.sales_person] or self.doc.owner,
						"subject": description,
						"description": description,
						"starts_on": key["scheduled_date"] + " 10:00:00",
						"event_type": "Private",
						"ref_type": self.doc.doctype,
						"ref_name": self.doc.name
					}).insert()

		webnotes.conn.set(self.doc, 'status', 'Submitted')		
		
	#get schedule dates
	#----------------------
	def create_schedule_list(self, start_date, end_date, no_of_visit, sales_person):
		schedule_list = []		
		start_date_copy = start_date
		date_diff = (getdate(end_date) - getdate(start_date)).days
		add_by = date_diff / no_of_visit

		while (getdate(start_date_copy) < getdate(end_date)):
			start_date_copy = add_days(start_date_copy, add_by)
			if len(schedule_list) < no_of_visit:
				schedule_date = self.validate_schedule_date_for_holiday_list(getdate(start_date_copy), 
					sales_person)
				if schedule_date > getdate(end_date):
					schedule_date = getdate(end_date)
				schedule_list.append(schedule_date)

		return schedule_list

	def validate_schedule_date_for_holiday_list(self, schedule_date, sales_person):
		from erpnext.accounts.utils import get_fiscal_year
		validated = False
		fy_details = ""

		try:
			fy_details = get_fiscal_year(date=schedule_date, verbose=0)
		except Exception:
			pass

		if fy_details and fy_details[0]:
			holiday_list = webnotes.conn.sql_list("""select h.holiday_date from `tabEmployee` emp, 
				`tabSales Person` sp, `tabHoliday` h, `tabHoliday List` hl 
				where sp.name=%s and emp.name=sp.employee 
				and hl.name=emp.holiday_list and 
				h.parent=hl.name and 
				hl.fiscal_year=%s""", (sales_person, fy_details[0]))
			if not holiday_list:
				holiday_list = webnotes.conn.sql("""select h.holiday_date from 
					`tabHoliday` h, `tabHoliday List` hl 
					where h.parent=hl.name and ifnull(hl.is_default, 0) = 1 
					and hl.fiscal_year=%s""", fy_details[0])

			while not validated and holiday_list:
				if schedule_date in holiday_list:
					schedule_date = add_days(schedule_date, -1)
				else:
					validated = True

		return schedule_date

	#validate date range and periodicity selected
	#-------------------------------------------------
	def validate_period(self, arg):
		args = eval(arg)
		if getdate(args['start_date']) >= getdate(args['end_date']):
			throw(_("Start date should be less than end date."))

		period = (getdate(args['end_date']) - getdate(args['start_date'])).days + 1

		if (args['periodicity'] == 'Yearly' or args['periodicity'] == 'Half Yearly' or 
			args['periodicity'] == 'Quarterly') and period < 365:
			throw(cstr(args['periodicity']) + " periodicity can be set for period of atleast 1 year or more only")
		elif args['periodicity'] == 'Monthly' and period < 30:
			throw("Monthly periodicity can be set for period of atleast 1 month or more")
		elif args['periodicity'] == 'Weekly' and period < 7:
			throw("Weekly periodicity can be set for period of atleast 1 week or more")
	
	def get_no_of_visits(self, arg):
		args = eval(arg)
		self.validate_period(arg)
		period = (getdate(args['end_date']) - getdate(args['start_date'])).days + 1
		count = 0

		if args['periodicity'] == 'Weekly':
			count = period/7
		elif args['periodicity'] == 'Monthly':
			count = period/30
		elif args['periodicity'] == 'Quarterly':
			count = period/91	 
		elif args['periodicity'] == 'Half Yearly':
			count = period/182
		elif args['periodicity'] == 'Yearly':
			count = period/365
		
		ret = {'no_of_visits' : count}
		return ret

	def validate_maintenance_detail(self):
		if not getlist(self.doclist, 'item_maintenance_detail'):
			throw(_("Please enter Maintaince Details first"))
		
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			if not d.item_code:
				throw(_("Please select item code"))
			elif not d.start_date or not d.end_date:
				throw(_("Please select Start Date and End Date for item") + " " + d.item_code)
			elif not d.no_of_visits:
				throw(_("Please mention no of visits required"))
			elif not d.sales_person:
				throw(_("Please select Incharge Person's name"))
			
			if getdate(d.start_date) >= getdate(d.end_date):
				throw(_("Start date should be less than end date for item") + " " + d.item_code)
	
	#check if maintenance schedule already created against same sales order
	#-----------------------------------------------------------------------------------
	def validate_sales_order(self):
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			if d.prevdoc_docname:
				chk = webnotes.conn.sql("""select ms.name from `tabMaintenance Schedule` ms, 
					`tabMaintenance Schedule Item` msi where msi.parent=ms.name and 
					msi.prevdoc_docname=%s and ms.docstatus=1""", d.prevdoc_docname)
				if chk:
					throw("Maintenance Schedule against " + d.prevdoc_docname + " already exist")
	

	def validate_serial_no(self):
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			cur_s_no=[]			
			if d.serial_no:
				cur_serial_no = d.serial_no.replace(' ', '')
				cur_s_no = cur_serial_no.split(',')
				
				for x in cur_s_no:
					chk = webnotes.conn.sql("""select name, status from `tabSerial No` 
						where docstatus!=2 and name=%s""", (x))
					chk1 = chk and chk[0][0] or ''
					status = chk and chk[0][1] or ''
					
					if not chk1:
						throw("Serial no " + x + " does not exist in system.")
	
	def validate(self):
		self.validate_maintenance_detail()
		self.validate_sales_order()
		self.validate_serial_no()
		self.validate_start_date()
	
	# validate that maintenance start date can not be before serial no delivery date
	#-------------------------------------------------------------------------------------------
	def validate_start_date(self):
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			if d.serial_no:
				cur_serial_no = d.serial_no.replace(' ', '')
				cur_s_no = cur_serial_no.split(',')
				
				for x in cur_s_no:
					dt = webnotes.conn.sql("""select delivery_date from `tabSerial No` 
						where name=%s""", x)
					dt = dt and dt[0][0] or ''
					
					if dt:
						if dt > getdate(d.start_date):
							throw("Maintenance start date can not be before delivery date " + dt.strftime('%Y-%m-%d') + " for serial no " + x)
	
	#update amc expiry date in serial no
	#------------------------------------------
	def update_amc_date(self,serial_no,amc_end_date):
		#get current list of serial no
		cur_serial_no = serial_no.replace(' ', '')
		cur_s_no = cur_serial_no.split(',')
		
		for x in cur_s_no:
			webnotes.conn.sql("""update `tabSerial No` set amc_expiry_date=%s, 
				maintenance_status='Under AMC' where name=%s""", (amc_end_date, x))
	
	def on_update(self):
		webnotes.conn.set(self.doc, 'status', 'Draft')
	
	def validate_serial_no_warranty(self):
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			if cstr(d.serial_no).strip():
				dt = webnotes.conn.sql("""select warranty_expiry_date, amc_expiry_date 
					from `tabSerial No` where name=%s""", d.serial_no, as_dict=1)
				if dt[0]['warranty_expiry_date'] and dt[0]['warranty_expiry_date'] >= d.start_date:
					throw("""Serial No: %s is already under warranty upto %s. 
						Please check AMC Start Date.""" % 
						(d.serial_no, dt[0]["warranty_expiry_date"]))
						
				if dt[0]['amc_expiry_date'] and dt[0]['amc_expiry_date'] >= d.start_date:
					throw("""Serial No: %s is already under AMC upto %s.
						Please check AMC Start Date.""" % 
						(d.serial_no, dt[0]["amc_expiry_date"]))

	def validate_schedule(self):
		item_lst1 =[]
		item_lst2 =[]
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			if d.item_code not in item_lst1:
				item_lst1.append(d.item_code)
		
		for m in getlist(self.doclist, 'maintenance_schedule_detail'):
			if m.item_code not in item_lst2:
				item_lst2.append(m.item_code)
		
		if len(item_lst1) != len(item_lst2):
			throw("Maintenance Schedule is not generated for all the items. Please click on 'Generate Schedule'")
		else:
			for x in item_lst1:
				if x not in item_lst2:
					throw("Maintenance Schedule is not generated for item "+x+". Please click on 'Generate Schedule'")
	
	#check if serial no present in item maintenance table
	#-----------------------------------------------------------
	def check_serial_no_added(self):
		serial_present =[]
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			if d.serial_no:
				serial_present.append(d.item_code)
		
		for m in getlist(self.doclist, 'maintenance_schedule_detail'):
			if serial_present:
				if m.item_code in serial_present and not m.serial_no:
					throw("Please click on 'Generate Schedule' to fetch serial no added for item "+m.item_code)

	def on_cancel(self):
		for d in getlist(self.doclist, 'item_maintenance_detail'):
			if d.serial_no:
				self.update_amc_date(d.serial_no, '')
		webnotes.conn.set(self.doc, 'status', 'Cancelled')
		delete_events(self.doc.doctype, self.doc.name)

	def on_trash(self):
		delete_events(self.doc.doctype, self.doc.name)

@webnotes.whitelist()
def make_maintenance_visit(source_name, target_doclist=None):
	from webnotes.model.mapper import get_mapped_doclist
	
	def update_status(source, target, parent):
		target.maintenance_type = "Scheduled"
	
	doclist = get_mapped_doclist("Maintenance Schedule", source_name, {
		"Maintenance Schedule": {
			"doctype": "Maintenance Visit", 
			"field_map": {
				"name": "maintenance_schedule"
			},
			"validation": {
				"docstatus": ["=", 1]
			},
			"postprocess": update_status
		}, 
		"Maintenance Schedule Item": {
			"doctype": "Maintenance Visit Purpose", 
			"field_map": {
				"parent": "prevdoc_docname", 
				"parenttype": "prevdoc_doctype",
				"sales_person": "service_person"
			}
		}
	}, target_doclist)

	return [d.fields for d in doclist]