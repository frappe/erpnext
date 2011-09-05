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


class DocType:
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist
  
  def get_employee_name(self):
    emp_nm = sql("select employee_name from `tabEmployee` where name=%s", self.doc.employee)
    emp_nm= emp_nm and emp_nm[0][0] or ''
    self.doc.employee_name = emp_nm
    return emp_nm
  
  def fetch_kra(self):
    if not self.doc.kra_template:
      msgprint("Please select KRA Template to be be fetched")
      raise Exception
    self.doc.clear_table(self.doclist,'appraisal_details')
    get_obj('DocType Mapper', 'KRA Template-Appraisal').dt_map('KRA Template', 'Appraisal', self.doc.kra_template, self.doc, self.doclist, "[['KRA Template','Appraisal'],['KRA Sheet', 'Appraisal Detail']]")
  
  def validate_dates(self):
    if getdate(self.doc.start_date) > getdate(self.doc.end_date):
      msgprint("End Date can not be less than Start Date")
      raise Exception
  
  def validate_existing_appraisal(self):
    chk = sql("select name from `tabAppraisal` where employee=%s and (status='Submitted' or status='Completed') and ((start_date>=%s and start_date<=%s) or (end_date>=%s and end_date<=%s))",(self.doc.employee,self.doc.start_date,self.doc.end_date,self.doc.start_date,self.doc.end_date))
    if chk:
      msgprint("You have already created Appraisal "+cstr(chk[0][0])+" in the current date range for employee "+cstr(self.doc.employee_name))
      raise Exception
  
  def validate_curr_appraisal(self):
    for d in getlist(self.doclist, 'appraisal_details'):
      if d.target_achieved or d.score:
        if self.doc.status == 'Draft':
          msgprint("Target achieved or Score can be added only for submitted Appraisal")
          raise Exception
        elif self.doc.status == 'Submitted' and session['user'] != self.doc.kra_approver:
          msgprint("Target achieved or Score can be added only by Appraisal Approver")
          raise Exception
  
  def validate_fiscal_year(self):
    fy=sql("select year_start_date from `tabFiscal Year` where name='%s'"%self.doc.fiscal_year)
    ysd=fy and fy[0][0] or ""
    yed=add_days(str(ysd),365)
    if str(self.doc.start_date) < str(ysd) or str(self.doc.start_date) > str(yed) or str(self.doc.end_date) < str(ysd) or str(self.doc.end_date) > str(yed):
      msgprint("Appraisal date range is not within the Fiscal Year selected")
      raise Exception
  
  def validate(self):
    self.validate_dates()
    self.validate_existing_appraisal()
    self.validate_curr_appraisal()
    self.validate_fiscal_year()
  
  def set_approver(self):
    ret={}
    approver_lst =[]
    emp_nm = self.get_employee_name()
    approver_lst1 = get_obj('Authorization Control').get_approver_name(self.doc.doctype,0,self)
    if approver_lst1:
      approver_lst=approver_lst1
    else:
      approver_lst = [x[0] for x in sql("select distinct name from `tabProfile` where enabled=1 and name!='Administrator' and name!='Guest' and docstatus!=2")]
    ret = {'app_lst':"\n" + "\n".join(approver_lst), 'emp_nm':cstr(emp_nm)}
    return ret
  
  def calculate_total(self):
    total = 0
    for d in getlist(self.doclist, 'appraisal_details'):
      if d.score:
        total = total + flt(d.score_earned)
    ret={'total_score':flt(total)}
    return ret
  
  def declare_completed(self):
    ret={}
    for d in getlist(self.doclist, 'appraisal_details'):
      if not d.target_achieved or not d.score or not d.score_earned:
        msgprint("Please add 'Target Achieved' and 'Score' for all KPI")
        ret = {'status':'Incomplete'}
        return ret
    
    if not self.doc.total_score:
      msgprint("Please calculate total score using button 'Calculate Total Score'")
      ret = {'status':'No Score'}
      return ret
    self.update_appraisal()
    #set(self.doc, 'status', 'Completed')
    ret = {'status':'Completed'}
    return ret
  
  def update_appraisal(self):
    for d in getlist(self.doclist, 'appraisal_details'):
      if not d.kra or not d.per_weightage:
        msgprint("Please remove the extra blank row added")
        raise Exception
      d.save()
    if self.doc.total_score:
      set(self.doc,'total_score',self.doc.total_score)
  
  def on_update(self):
    set(self.doc, 'status', 'Draft')
  
  def validate_total_weightage(self):
    total_w = 0
    for d in getlist(self.doclist, 'appraisal_details'):
      total_w = flt(total_w) + flt(d.per_weightage)
    
    if flt(total_w)>100 or flt(total_w)<100:
      msgprint("Total of weightage assigned to KPI is "+cstr(total_w)+".It should be 100(%)")
      raise Exception
  
  def validate_appraisal_detail(self):
    if not self.doc.kra_approver:
      msgprint("Please mention the name of Approver")
      raise Exception
    
    if not getlist(self.doclist, 'appraisal_details'):
      msgprint("Please add KRA Details")
      raise Exception    
    
    self.validate_total_weightage()
  
  def on_submit(self):
    self.validate_appraisal_detail()
    set(self.doc, 'status', 'Submitted')
  
  def on_cancel(self): 
    set(self.doc, 'status', 'Cancelled')