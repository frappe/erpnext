# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes import session, msgprint, errprint

sql = webnotes.conn.sql
convert_to_lists = webnotes.conn.convert_to_lists

try: import json
except: import simplejson as json

# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

# --------------------------------------------------------------------------------------------------------
# ------------------------------------- Home page module details -----------------------------------------
	
	def delete_cache(self):
		com = sql("select abbr, name from tabCompany")
		for d in com:
			sql("update `tabCompany` set receivables_group = '%s' where (receivables_group = '%s' or receivables_group = '' or receivables_group is null) and name = '%s'" % ('Accounts Receivable - '+cstr(d[0]), 'Accounts Receivables - '+cstr(d[0]), d[1]))
			sql("update `tabCompany` set payables_group = '%s' where (payables_group = '%s' or payables_group = '' or payables_group is null) and name = '%s'" % ('Accounts Payable - '+cstr(d[0]), 'Accounts Payables - '+cstr(d[0]), d[1]))

	def get_modules(self):
		rl = webnotes.user.get_roles()
		ml = sql("select distinct t1.name, t1.module_icon, t1.module_label, t1.module_desc, t1.module_page from  `tabModule Def` t1, `tabModule Def Role` t2 where t2.role in ('%s') and t1.disabled !='Yes' and ifnull(t1.is_hidden, 'No') != 'Yes' and t1.name = t2.parent order by t1.module_seq asc" % "','".join(rl), as_dict=1)
		webnotes.response['login_url'] = session['data'].get('login_from', '')		
		
		return ml

	def get_module_details(self,m):
		ret = {}
		ret['il'] = sql('select doc_type, doc_name, display_name, icon, description, fields, click_function, idx from `tabModule Def Item` where parent=%s and ifnull(`hide`,0)=0 order by idx asc', m, as_dict=1)
		ret['wl'] = sql('select widget_code from `tabModule Def` where name =%s', m)[0][0] or ''
		ret['custom_reports'] = sql('''
			SELECT DISTINCT t1.criteria_name AS `display_name`, t1.description, t1.doc_type AS `doc_name`, 'Custom Reports' AS `doc_type` 
			FROM `tabSearch Criteria` t1, `tabDocPerm` t2 
			WHERE t1.module = "%s" 
			AND IFNULL(t1.disabled,0) = 0 
			AND (t1.doc_type=t2.parent OR t1.parent_doc_type = t2.parent) 
			AND t2.permlevel = 0 
			AND t2.read=1 
			AND t2.role IN ("%s") 
			AND ifnull(standard,"No")="No"''' % (m, '", "'.join(webnotes.user.get_roles())), as_dict=1)

		return ret

	# ----------------------------------------------------------------------------------------------------------------
	# ----------------------------------------------- Home page updates ----------------------------------------------
	
	def get_events_list(self):
		import webnotes, webnotes.utils
		from webnotes.widgets.event import get_cal_events
		
		dl = get_cal_events(nowdate(), add_days(nowdate(), 7))
		el = []
		for d in dl:
			#el.append([d.name, d.event_date, d.event_hour, d.event_name, d.description or '', d.ref_type or '', d.ref_name or '', d.owner])
			dict = {
				'name': d.name,
				'event_date': d.event_date,
				'event_hour': d.event_hour,
				'event_name': d.event_name,
				'description': d.description,
				'notes': d.notes,
				'event_type': d.event_type,
				'ref_type': d.ref_type,
				'ref_name': d.ref_name,
				'owner' : d.owner
			}
			
			el.append(dict)
		return el

		
	def get_activity_list(self):
		out = {}
		import webnotes
		rt = webnotes.user.can_read
    
		dt_list = [d[0] for d in sql("select distinct t2.name from tabDocField t1, tabDocType t2 where t1.fieldname='status' and t1.docstatus=0 and (t2.istable is null or t2.istable = 0) and t1.parent = t2.name")]
		if not dt_list:
			return out

		# get list of activity dt
		for dt in dt_list:
			if dt in rt:
				out[dt] = {}
				# get status list
				sl = sql("select distinct status from `tab%s`" % dt)
			
				for s in sl:
					if s[0]:
						# get count
						cnt = sql("select count(*) from `tab%s` where status = '%s' and modified > '%s'" % (dt, s[0], add_days(nowdate(), -7)))[0][0]
						out[dt][s[0]] = cint(cnt)
		return out
		
	def get_dt_help(self,dt):
		return sql("select description from tabDocType where name=%s",dt)[0][0] or ''

	# get dashboard counts
	# --------------------
	def get_wip_counts(self):
		#dtl = ['Lead', 'Enquiries', 'Sales Order', 'Invoices', 'Purchase Request', 'Purchase Order', 'Bills', 'Tasks', 'Delivery Note', 'Maintenance']
		can_read_dt = ['Lead', 'Opportunity', 'Sales Order', 'Sales Invoice', 'Purchase Request', 'Purchase Order', 'Purchase Invoice', 'Delivery Note', 'Task', 'Serial No']
		dt = {}
		for d in can_read_dt:
			args = {}
			
			# if Lead
			if d=='Lead':
				args = {'To follow up':sql("select count(name) from tabLead where status!='Converted' and status!='Lead Lost' and status!='Not Interested'")}

			# if Opportunity
			elif d=='Opportunity':
				args['Quotations to be sent'] = sql("select count(distinct(t2.name)) from `tabQuotation`t1, `tabOpportunity`t2 where t1.enq_no!=t2.name and t2.docstatus=1")
				args['To follow up'] = sql("select count(distinct(t2.name)) from `tabQuotation`t1, `tabOpportunity`t2 where t1.enq_no=t2.name and t2.docstatus=1 and t1.docstatus=1")

			# if Sales Order
			elif d=='Sales Order':
				args['To be delivered'] = sql("select count(name) from `tabSales Order` where ifnull(per_delivered,0)<100 and delivery_date>now() and docstatus=1")
				args['To be billed'] = sql("select count(name) from `tabSales Order` where ifnull(per_billed,0)<100 and docstatus=1")
				args['Overdue'] = sql("select count(name) from `tabSales Order` where ifnull(per_delivered,0)<100 and delivery_date<now() and docstatus=1")
				args['To be submitted'] = sql("select count(name) from `tabSales Order` where docstatus=0 and status='Draft'")      #Draft

			# if Sales Invoice
			elif d=='Sales Invoice':
				args['To receive payment'] = sql("select count(name) from `tabSales Invoice` where docstatus=1 and due_date>now() and outstanding_amount!=0")
				args['Overdue'] = sql("select count(name) from `tabSales Invoice` where docstatus=1 and due_date<now() and outstanding_amount!=0")  
				args['To be submitted'] = sql("select count(name) from `tabSales Invoice` where docstatus=0")       #Draft

			# if Purchase Request 
			elif d=='Purchase Request':
				args['Purchase Order to be made'] = sql("select count(name) from `tabPurchase Request` where ifnull(per_ordered,0)<100 and docstatus=1")
				args['To be submitted'] = sql("select count(name) from `tabPurchase Request` where status='Draft'")      #Draft

			# if Purchase Order    
			elif d=='Purchase Order':
				args['To receive items'] = sql("select count(name) from `tabPurchase Order` where ifnull(per_received,0)<100 and docstatus=1")
				args['To be billed'] = sql("select count(name) from `tabPurchase Order` where ifnull(per_billed,0)<100 and docstatus=1")
				args['To be submitted'] = sql("select count(name) from `tabPurchase Order` where status='Draft'")        #Draft

			# if Purchase Invoice
			elif d=='Purchase Invoice':
				args['To be paid'] = sql("select count(name) from `tabPurchase Invoice` where docstatus=1 and outstanding_amount!=0")
				args['To be submitted'] = sql("select count(name) from `tabPurchase Invoice` where docstatus=0")       #Draft

			# if Delivery Note
			elif d=='Delivery Note':
				args['To be submitted'] = sql("select count(name) from `tabDelivery Note` where status='Draft' and docstatus=0")
				args['To be billed'] = sql("select count(name) from `tabDelivery Note` where docstatus=1 and docstatus=1 and ifnull(per_billed,0)<100")
			
			# if Tasks
			elif d=='Task':
				args = {'Open': sql("select count(name) from `tabTask` where status='Open'")}

			# if Serial No
			elif d=='Serial No':
				args['AMC expiring this month'] = sql("select count(name) from `tabSerial No` where docstatus!=2 and maintenance_status = 'Under AMC' and status!='Scrapped' and status!='Not in Use' and month(now()) = month(amc_expiry_date) and year(now()) = year(amc_expiry_date)")
				args['Warranty expiring this month'] = sql("select count(name) from `tabSerial No` where docstatus!=2 and maintenance_status = 'Under Warranty' and status!='Scrapped' and status!='Not in Use' and month(now()) = month(ifnull(warranty_expiry_date,0)) and year(now())=year(ifnull(warranty_expiry_date,0))")
			
			for a in args:
				args[a] = args[a] and args[a][0][0] or 0
			
			dt[d] = args
		return dt

	# -------------------------------------------------------------------------------------------------------
	
	def get_todo_count(self):
		count = sql("select count(distinct name) from `tabToDo` where owner=%s", session['user'])
		count = count and count[0][0] or 0
		return count
		
	def get_todo_list(self):
		res = sql("""select name, description, `date`, 
			priority, checked, reference_type, reference_name from `tabToDo` 
			where owner=%s order by field(priority,'High','Medium','Low') asc, date asc""", \
				session['user'], as_dict=1)
		return res
		
	def add_todo_item(self,args):
		args = json.loads(args)

		d = Document('ToDo', args.get('name') or None)
		d.description = args['description']
		d.date = args['date']
		d.priority = args['priority']
		d.checked = args.get('checked', 0)
		d.owner = session['user']
		d.save(not args.get('name') and 1 or 0)

		if args.get('name') and d.checked:
			self.notify_assignment(d)
	
		return d.name

	def remove_todo_item(self,nm):
		d = Document('ToDo', nm or None)
		if d and d.name:
			self.notify_assignment(d)
		sql("delete from `tabToDo` where name = %s",nm)

	def notify_assignment(self, d):
		doc_type = d.fields.get('reference_type')
		doc_name = d.fields.get('reference_name')
		assigned_by = d.fields.get('assigned_by')
		if doc_type and doc_name and assigned_by:
			from webnotes.widgets.form import assign_to
			assign_to.notify_assignment(assigned_by, d.owner, doc_type, doc_name)



	# -------------------------------------------------------------------------------------------------------

	def dismiss_message(self, arg=''):
		msg_id = webnotes.conn.get_global('system_message_id')
		webnotes.conn.set_global('system_message_id', msg_id, session['user'])
		
	# -------------------------------------------------------------------------------------------------------

	def get_todo_reminder(self):
		return convert_to_lists(sql("select name, description, date, priority,checked from `tabToDo` where owner=%s and date=%s and checked=1 order by priority, date", (session['user'], nowdate())))
		
	# get user details
	def get_users(self):
		ret = {}
		ret['usr'] = convert_to_lists(sql("select distinct name, concat_ws(' ', first_name, last_name), ifnull(messanger_status,'Available') from tabProfile where name=%s", session['user']))
		ret['on'] = convert_to_lists(sql("select distinct t1.name, concat_ws(' ', t1.first_name, t1.last_name), ifnull(t1.messanger_status,'Available') from tabProfile t1, tabSessions t2 where t1.name = t2.user and t1.name not in('Guest',%s) and TIMESTAMPDIFF(HOUR,t2.lastupdate,NOW()) <= 1", session['user']))
		ret['off'] = convert_to_lists(sql("select distinct t1.name, concat_ws(' ', t1.first_name, t1.last_name), ifnull(t1.messanger_status,'Offline') from tabProfile t1, tabSessions t2 where t1.name != t2.user and t1.name not in('Guest',%s) and t1.name not in(select distinct t1.name from tabProfile t1, tabSessions t2 where t1.name = t2.user and t1.name not in('Guest',%s) and (t1.messanger_status !='Invisible' or t1.messanger_status is null) and TIMESTAMPDIFF(HOUR,t2.lastupdate,NOW()) <= 1)", (session['user'], session['user'])))

		return ret
		
	# Delete event
	def delete_event(self,id):
		sql("delete from tabEvent where name=%s", id)
		
	# edit event
	def edit_event(self,arg):
		arg = json.loads(arg)
		d = Document('Event', arg.get('name') or None)
		for k in arg:
			d.fields[k] = str(arg[k])
		d.save(not arg.get('name') and 1 or 0)
	
	# -------------------------------------------------------------------------------------------------------
	# module settings
	# -------------------------------------------------------------------------------------------------------
	def get_module_order(self):
		show_list = ['Home','Setup','Accounts','Selling','Buying','Support','Stock','HR','Projects','Analysis','Production']
		ml = filter(lambda x: x[0] in show_list, \
			sql("select name, module_label, module_seq, is_hidden from `tabModule Def` where docstatus<2 order by module_seq asc, module_label asc"))
		return convert_to_lists(ml)
			
	def set_module_order(self,arg):
		arg = eval(arg)
		for k in arg:
			sql("update `tabModule Def` set module_seq = %s, is_hidden = %s where name = %s", (cint(arg[k]['module_seq']) + 1, arg[k]['is_hidden'], k))

	# -------------------------------------------------------------------------------------------------------

	def get_bd_list(self):
		bl = convert_to_lists(sql("select name,concat_ws(' ',first_name,last_name),birth_date from tabProfile where (birth_date is not null and birth_date != '') and (enabled is not null and enabled !='')"))

		nd = nowdate().split('-')
		d = cint(nd[2])
		m = cint(nd[1])

		tb = []
		for b in bl:
			if b[2] and b[2].find('-') != -1:
				if cint(b[2].split('-')[2]) == d and cint(b[2].split('-')[1]) == m:
					tb.append(b)

		return tb

	# obtain account id for webforms
	def get_acc_id(self):
		acc_id = sql("select value from `tabSingles` where field='account_id' and doctype='Control Panel'")
		acc_id = acc_id and acc_id[0][0] or ''
		if acc_id:
			return cstr(acc_id)
		else:
			msgprint("Account Id not specified")
			raise Exception
  
	#update serial no status
	def update_serial_status(self, lst, status):
		lst11=[]
		for y1 in lst:
			sql("update `tabSerial No` set maintenance_status = %s where name=%s", (status,y1))
			lst11.append(y1)
			msgprint("Status updated as '"+status+"' for "+cstr(lst11))

	# chk to set serial no status as 'Out of warranty'
	def set_for_out_of_warranty(self):
		chk_for_out_of_wrnty = sql("select name from `tabSerial No` where ifnull(warranty_expiry_date, '2200-12-12') < CURDATE() and ifnull(warranty_expiry_date, '0000-00-00') != '0000-00-00' and ifnull(amc_expiry_date, '0000-00-00') ='0000-00-00' and ifnull(maintenance_status, '') != 'Out of Warranty'")
		if chk_for_out_of_wrnty:
			lst1 = [x1[0] for x1 in chk_for_out_of_wrnty]
			self.update_serial_status(lst1, 'Out Of Warranty')
        
	# chk to set serial no status as 'Out of amc'
	def set_for_out_of_amc(self):
		chk_for_out_of_amc = sql("select name from `tabSerial No` where ifnull(warranty_expiry_date, '0000-00-00')< CURDATE() and ifnull(amc_expiry_date, '2200-12-12') < CURDATE() and ifnull(amc_expiry_date, '0000-00-00') !='0000-00-00' and ifnull(maintenance_status, '') !='Out of AMC'")
		if chk_for_out_of_amc:
			lst2 = [x2[0] for x2 in chk_for_out_of_amc]
			self.update_serial_status(lst2, 'Out Of AMC')
         
	# chk to set serial no status as 'under amc'
	def set_for_under_amc(self):
		chk_for_under_amc = sql("select name from `tabSerial No` where ifnull(warranty_expiry_date, '0000-00-00')< CURDATE() and ifnull(amc_expiry_date, '2200-12-12') >= CURDATE() and ifnull(amc_expiry_date, '0000-00-00') !='0000-00-00' and ifnull(maintenance_status, '') !='Under AMC'")
		if chk_for_under_amc:
			lst3 = [x3[0] for x3 in chk_for_under_amc]
			self.update_serial_status(lst3, 'Under AMC')

	# chk to set serial no status as 'under warranty'
	def set_for_under_warranty(self):
		chk_for_under_wrnty = sql("select name from `tabSerial No` where ifnull(warranty_expiry_date, '2200-12-12') >= CURDATE() and ifnull(warranty_expiry_date, '0000-00-00') != '0000-00-00' and ifnull(amc_expiry_date, '0000-00-00') ='0000-00-00' and ifnull(maintenance_status, '') != 'Under Warranty'")
		if chk_for_under_wrnty:
			lst4 = [x4[0] for x4 in chk_for_under_wrnty]
			self.update_serial_status(lst4, 'Under Warranty')
  
	# check maintenance status for all serial nos only for 1st login each day
	def set_serial_no_status(self):

		chk_serial_no_update_date = webnotes.conn.get_global('maintenance_status_update_date')

		# check status only for 1st login each day.... if maintenance date already updated means it is checked
		if getdate(chk_serial_no_update_date) != nowdate():
			# chk to set serial no status as 'Out of warranty'
			self.set_for_out_of_warranty()                        

			# chk to set serial no status as 'Out of amc'
			self.set_for_out_of_amc()

			# chk to set serial no status as 'under amc'
			self.set_for_under_amc()

			# chk to set serial no status as 'under warranty'
			self.set_for_under_warranty()

			#set maintenance_status_update_date
			webnotes.conn.set_global('maintenance_status_update_date', nowdate())
			
	# get user fullname
	def get_user_fullname(self,usr):	
		return sql("select concat_ws(' ',first_name, last_name) from tabProfile where name=%s", usr)[0][0] or ''
