# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import add_days, cstr, getdate, cint

from frappe import throw, _
from erpnext.utilities.transaction_base import TransactionBase, delete_events
from erpnext.stock.utils import get_valid_serial_nos

class MaintenanceSchedule(TransactionBase):
	
	def get_item_details(self, item_code):
		item = frappe.db.sql("""select item_name, description from `tabItem` 
			where name=%s""", (item_code), as_dict=1)
		ret = {
			'item_name': item and item[0]['item_name'] or '',
			'description' : item and item[0]['description'] or ''
		}
		return ret
		
	def generate_schedule(self):
		self.set('maintenance_schedule_detail', [])
		frappe.db.sql("""delete from `tabMaintenance Schedule Detail` 
			where parent=%s""", (self.name))
		count = 1
		for d in self.get('item_maintenance_detail'):
			self.validate_maintenance_detail()
			s_list = []
			s_list = self.create_schedule_list(d.start_date, d.end_date, d.no_of_visits, d.sales_person)
			for i in range(d.no_of_visits):
				child = self.append('maintenance_schedule_detail')
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
		if not self.get('maintenance_schedule_detail'):
			throw("Please click on 'Generate Schedule' to get schedule")
		self.check_serial_no_added()
		self.validate_schedule()

		email_map = {}
		for d in self.get('item_maintenance_detail'):
			if d.serial_no:
				serial_nos = get_valid_serial_nos(d.serial_no)
				self.validate_serial_no(serial_nos, d.start_date)
				self.update_amc_date(serial_nos, d.end_date)

			if d.sales_person not in email_map:
				sp = frappe.get_doc("Sales Person", d.sales_person).make_controller()
				email_map[d.sales_person] = sp.get_email_id()

			scheduled_date = frappe.db.sql("""select scheduled_date from 
				`tabMaintenance Schedule Detail` where sales_person=%s and item_code=%s and 
				parent=%s""", (d.sales_person, d.item_code, self.name), as_dict=1)

			for key in scheduled_date:
				if email_map[d.sales_person]:
					description = "Reference: %s, Item Code: %s and Customer: %s" % \
						(self.name, d.item_code, self.customer)
					frappe.get_doc({
						"doctype": "Event",
						"owner": email_map[d.sales_person] or self.owner,
						"subject": description,
						"description": description,
						"starts_on": key["scheduled_date"] + " 10:00:00",
						"event_type": "Private",
						"ref_type": self.doctype,
						"ref_name": self.name
					}).insert(ignore_permissions=1)

		frappe.db.set(self, 'status', 'Submitted')		

	def create_schedule_list(self, start_date, end_date, no_of_visit, sales_person):
		schedule_list = []		
		start_date_copy = start_date
		date_diff = (getdate(end_date) - getdate(start_date)).days
		add_by = date_diff / no_of_visit

		for visit in range(cint(no_of_visit)):
			if (getdate(start_date_copy) < getdate(end_date)):
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
			# check holiday list in employee master
			holiday_list = frappe.db.sql_list("""select h.holiday_date from `tabEmployee` emp, 
				`tabSales Person` sp, `tabHoliday` h, `tabHoliday List` hl 
				where sp.name=%s and emp.name=sp.employee 
				and hl.name=emp.holiday_list and 
				h.parent=hl.name and 
				hl.fiscal_year=%s""", (sales_person, fy_details[0]))
			if not holiday_list:
				# check global holiday list
				holiday_list = frappe.db.sql("""select h.holiday_date from 
					`tabHoliday` h, `tabHoliday List` hl 
					where h.parent=hl.name and ifnull(hl.is_default, 0) = 1 
					and hl.fiscal_year=%s""", fy_details[0])

			if not validated and holiday_list:
				if schedule_date in holiday_list:
					schedule_date = add_days(schedule_date, -1)
				else:
					validated = True

		return schedule_date

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
		if not self.get('item_maintenance_detail'):
			throw(_("Please enter Maintaince Details first"))
		
		for d in self.get('item_maintenance_detail'):
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
	
	def validate_sales_order(self):
		for d in self.get('item_maintenance_detail'):
			if d.prevdoc_docname:
				chk = frappe.db.sql("""select ms.name from `tabMaintenance Schedule` ms, 
					`tabMaintenance Schedule Item` msi where msi.parent=ms.name and 
					msi.prevdoc_docname=%s and ms.docstatus=1""", d.prevdoc_docname)
				if chk:
					throw("Maintenance Schedule against " + d.prevdoc_docname + " already exist")
	
	def validate(self):
		self.validate_maintenance_detail()
		self.validate_sales_order()
	
	def on_update(self):
		frappe.db.set(self, 'status', 'Draft')

	def update_amc_date(self, serial_nos, amc_expiry_date=None):
		for serial_no in serial_nos:
			serial_no_bean = frappe.get_doc("Serial No", serial_no)
			serial_no_bean.amc_expiry_date = amc_expiry_date
			serial_no_bean.save()

	def validate_serial_no(self, serial_nos, amc_start_date):
		for serial_no in serial_nos:
			sr_details = frappe.db.get_value("Serial No", serial_no, 
				["warranty_expiry_date", "amc_expiry_date", "status", "delivery_date"], as_dict=1)
			
			if sr_details.warranty_expiry_date and sr_details.warranty_expiry_date>=amc_start_date:
				throw("""Serial No: %s is already under warranty upto %s. 
					Please check AMC Start Date.""" % (serial_no, sr_details.warranty_expiry_date))
					
			if sr_details.amc_expiry_date and sr_details.amc_expiry_date >= amc_start_date:
				throw("""Serial No: %s is already under AMC upto %s.
					Please check AMC Start Date.""" % (serial_no, sr_details.amc_expiry_date))
					
			if sr_details.status=="Delivered" and sr_details.delivery_date and \
				sr_details.delivery_date >= amc_start_date:
					throw(_("Maintenance start date can not be before \
						delivery date for serial no: ") + serial_no)

	def validate_schedule(self):
		item_lst1 =[]
		item_lst2 =[]
		for d in self.get('item_maintenance_detail'):
			if d.item_code not in item_lst1:
				item_lst1.append(d.item_code)
		
		for m in self.get('maintenance_schedule_detail'):
			if m.item_code not in item_lst2:
				item_lst2.append(m.item_code)
		
		if len(item_lst1) != len(item_lst2):
			throw(_("Maintenance Schedule is not generated for all the items. \
				Please click on 'Generate Schedule'"))
		else:
			for x in item_lst1:
				if x not in item_lst2:
					throw(_("Maintenance Schedule is not generated for item ") + x + 
						_(". Please click on 'Generate Schedule'"))
	
	def check_serial_no_added(self):
		serial_present =[]
		for d in self.get('item_maintenance_detail'):
			if d.serial_no:
				serial_present.append(d.item_code)
		
		for m in self.get('maintenance_schedule_detail'):
			if serial_present:
				if m.item_code in serial_present and not m.serial_no:
					throw("Please click on 'Generate Schedule' to fetch serial no added for item "+m.item_code)

	def on_cancel(self):
		for d in self.get('item_maintenance_detail'):
			if d.serial_no:
				serial_nos = get_valid_serial_nos(d.serial_no)
				self.update_amc_date(serial_nos)
		frappe.db.set(self, 'status', 'Cancelled')
		delete_events(self.doctype, self.name)

	def on_trash(self):
		delete_events(self.doctype, self.name)

@frappe.whitelist()
def make_maintenance_visit(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	
	def update_status(source, target, parent):
		target.maintenance_type = "Scheduled"
	
	doclist = get_mapped_doc("Maintenance Schedule", source_name, {
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
	}, target_doc)

	return doclist.as_dict()