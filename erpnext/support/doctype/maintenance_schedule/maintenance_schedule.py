# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist
  
  # pull sales order details
  #--------------------------
  def pull_sales_order_detail(self):
    self.doc.clear_table(self.doclist, 'item_maintenance_detail')
    self.doc.clear_table(self.doclist, 'maintenance_schedule_detail')
    self.doclist = get_obj('DocType Mapper', 'Sales Order-Maintenance Schedule').dt_map('Sales Order', 'Maintenance Schedule', self.doc.sales_order_no, self.doc, self.doclist, "[['Sales Order', 'Maintenance Schedule'],['Sales Order Detail', 'Item Maintenance Detail']]")
  
  #pull item details 
  #-------------------
  def get_item_details(self, item_code):
    item = sql("select item_name, description from `tabItem` where name = '%s'" %(item_code), as_dict=1)
    ret = {
      'item_name': item and item[0]['item_name'] or '',
      'description' : item and item[0]['description'] or ''
    }
    return ret
    
  # generate maintenance schedule
  #-------------------------------------
  def generate_schedule(self):
    import datetime
    self.doc.clear_table(self.doclist, 'maintenance_schedule_detail')
    count = 0
    for d in getlist(self.doclist, 'item_maintenance_detail'):
      self.validate_maintenance_detail()
      s_list =[]
      s_list = self.create_schedule_list(d.start_date, d.end_date, d.no_of_visits)
      
      for i in range(d.no_of_visits):        
        child = addchild(self.doc,'maintenance_schedule_detail','Maintenance Schedule Detail',1,self.doclist)
        child.item_code = d.item_code
        child.scheduled_date = s_list[i].strftime('%Y-%m-%d')
        if d.serial_no:
          child.serial_no = d.serial_no
        child.idx = count
        count = count+1
        child.incharge_name = d.incharge_name
        child.save(1)
    self.on_update()
  
  #get schedule dates
  #----------------------
  def create_schedule_list(self, start_date, end_date, no_of_visit):
    schedule_list = []    
    start_date1 = start_date
    date_diff = (getdate(end_date) - getdate(start_date)).days
    add_by = date_diff/no_of_visit
    #schedule_list.append(start_date1)
    while(getdate(start_date1) < getdate(end_date)):
      start_date1 = add_days(start_date1, add_by)
      if len(schedule_list) < no_of_visit:
        schedule_list.append(getdate(start_date1))
    return schedule_list
  
  #validate date range and periodicity selected
  #-------------------------------------------------
  def validate_period(self, arg):
    arg1 = eval(arg)
    if getdate(arg1['start_date']) >= getdate(arg1['end_date']):
      msgprint("Start date should be less than end date ")
      raise Exception
    
    period = (getdate(arg1['end_date'])-getdate(arg1['start_date'])).days+1
    
    if (arg1['periodicity']=='Yearly' or arg1['periodicity']=='Half Yearly' or arg1['periodicity']=='Quarterly') and period<365:
      msgprint(cstr(arg1['periodicity'])+ " periodicity can be set for period of atleast 1 year or more only")
      raise Exception
    elif arg1['periodicity']=='Monthly' and period<30:
      msgprint("Monthly periodicity can be set for period of atleast 1 month or more")
      raise Exception
    elif arg1['periodicity']=='Weekly' and period<7:
      msgprint("Weekly periodicity can be set for period of atleast 1 week or more")
      raise Exception
  
  #get count on the basis of periodicity selected
  #----------------------------------------------------
  def get_no_of_visits(self, arg):
    arg1 = eval(arg)
    start_date = arg1['start_date']
    
    self.validate_period(arg)
    period = (getdate(arg1['end_date'])-getdate(arg1['start_date'])).days+1
    
    count =0
    if arg1['periodicity'] == 'Weekly':
      count = period/7
    elif arg1['periodicity'] == 'Monthly':
      count = period/30
    elif arg1['periodicity'] == 'Quarterly':
      count = period/91   
    elif arg1['periodicity'] == 'Half Yearly':
      count = period/182
    elif arg1['periodicity'] == 'Yearly':
      count = period/365
    
    ret = {'no_of_visits':count}
    return ret
  
  def validate_maintenance_detail(self):
    if not getlist(self.doclist, 'item_maintenance_detail'):
      msgprint("Please enter Maintaince Details first")
      raise Exception
    
    for d in getlist(self.doclist, 'item_maintenance_detail'):
      if not d.item_code:
        msgprint("Please select item code")
        raise Exception
      elif not d.start_date or not d.end_date:
        msgprint("Please select Start Date and End Date for item "+d.item_code)
        raise Exception
      elif not d.no_of_visits:
        msgprint("Please mention no of visits required")
        raise Exception
      elif not d.incharge_name:
        msgprint("Please select Incharge Person's name")
        raise Exception
      
      if getdate(d.start_date) >= getdate(d.end_date):
        msgprint("Start date should be less than end date for item "+d.item_code)
        raise Exception
  
  #check if maintenance schedule already created against same sales order
  #-----------------------------------------------------------------------------------
  def validate_sales_order(self):
    for d in getlist(self.doclist, 'item_maintenance_detail'):
      if d.prevdoc_docname:
        chk = sql("select t1.name from `tabMaintenance Schedule` t1, `tabItem Maintenance Detail` t2 where t2.parent=t1.name and t2.prevdoc_docname=%s and t1.docstatus=1", d.prevdoc_docname)
        if chk:
          msgprint("Maintenance Schedule against "+d.prevdoc_docname+" already exist")
          raise Exception
  
  # Validate values with reference document
  #----------------------------------------
  def validate_reference_value(self):
    get_obj('DocType Mapper', 'Sales Order-Maintenance Schedule', with_children = 1).validate_reference_value(self, self.doc.name)
  
  def validate_serial_no(self):
    for d in getlist(self.doclist, 'item_maintenance_detail'):
      cur_s_no=[]      
      if d.serial_no:
        cur_serial_no = d.serial_no.replace(' ', '')
        cur_s_no = cur_serial_no.split(',')
        
        for x in cur_s_no:
          chk = sql("select name, status from `tabSerial No` where docstatus!=2 and name=%s", (x))
          chk1 = chk and chk[0][0] or ''
          status = chk and chk[0][1] or ''
          
          if not chk1:
            msgprint("Serial no "+x+" does not exist in system.")
            raise Exception
          else:
            if status=='In Store' or status=='Note in Use' or status=='Scrapped':
              msgprint("Serial no "+x+" is '"+status+"'")
              raise Exception
  
  def validate(self):
    self.validate_maintenance_detail()
    self.validate_sales_order()
    if self.doc.sales_order_no:
      self.validate_reference_value()
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
          dt = sql("select delivery_date from `tabSerial No` where name = %s", x)
          dt = dt and dt[0][0] or ''
          
          if dt:
            if dt > getdate(d.start_date):
              msgprint("Maintenance start date can not be before delivery date "+dt.strftime('%Y-%m-%d')+" for serial no "+x)
              raise Exception
  
  #update amc expiry date in serial no
  #------------------------------------------
  def update_amc_date(self,serial_no,amc_end_date):
    #get current list of serial no
    cur_serial_no = serial_no.replace(' ', '')
    cur_s_no = cur_serial_no.split(',')
    
    for x in cur_s_no:
      sql("update `tabSerial No` set amc_expiry_date = '%s', maintenance_status = 'Under AMC' where name = '%s'"% (amc_end_date,x))
  
  def on_update(self):
    set(self.doc, 'status', 'Draft')
  
  #validate that new maintenance start date does not clash with existing mntc end date
  #-------------------------------------------------------------------------------------------------
  def validate_serial_no_warranty(self):
    for d in getlist(self.doclist, 'item_maintenance_detail'):
      if d.serial_no:
        dt = sql("select warranty_expiry_date, amc_expiry_date from `tabSerial No` where name = %s", d.serial_no, as_dict=1)
        
        if dt[0]['warranty_expiry_date']:
          if dt[0]['warranty_expiry_date'] >= getdate(d.start_date):
            msgprint("Serial no "+d.serial_no+" for item "+d.item_code+" is already under warranty till "+(dt[0]['warranty_expiry_date']).strftime('%Y-%m-%d')+". You can schedule AMC start date after "+(dt[0]['warranty_expiry_date']).strftime('%Y-%m-%d'))
            raise Exception
        if dt[0]['amc_expiry_date']:
          if dt[0]['amc_expiry_date'] >= getdate(d.start_date):
            msgprint("Serial no "+d.serial_no+" for item "+d.item_code+" is already under AMC till "+(dt[0]['amc_expiry_date']).strftime('%Y-%m-%d')+". You can schedule new AMC start date after "+(dt[0]['amc_expiry_date']).strftime('%Y-%m-%d'))
            raise Exception
  
  #validate if schedule generated for all items
  #-------------------------------------------------
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
      msgprint("Maintenance Schedule is not generated for all the items. Please click on 'Generate Schedule'")
      raise Exception
    else:
      for x in item_lst1:
        if x not in item_lst2:
          msgprint("Maintenance Schedule is not generated for item "+x+". Please click on 'Generate Schedule'")
          raise Exception
  
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
          msgprint("Please click on 'Generate Schedule' to fetch serial no added for item "+m.item_code)
          raise Exception
  
  def on_submit(self):
    if not getlist(self.doclist, 'maintenance_schedule_detail'):
      msgprint("Please click on 'Generate Schedule' to get schedule")
      raise Exception
    self.check_serial_no_added()
    self.validate_serial_no_warranty()
    self.validate_schedule()
    for d in getlist(self.doclist, 'item_maintenance_detail'):
      if d.serial_no:
        self.update_amc_date(d.serial_no, d.end_date)
    set(self.doc, 'status', 'Submitted')    

  
  def on_cancel(self):
    for d in getlist(self.doclist, 'item_maintenance_detail'):
      if d.serial_no:
        self.update_amc_date(d.serial_no, '')
    set(self.doc, 'status', 'Cancelled')
