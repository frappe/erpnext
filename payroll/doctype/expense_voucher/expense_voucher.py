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
    emp_dtl = sql("select employee_name,company_email from `tabEmployee` where name=%s", self.doc.employee)
    emp_nm = emp_dtl and emp_dtl[0][0] or ''
    self.doc.employee_name = emp_nm
    self.doc.email_id = emp_dtl and emp_dtl[0][1] or ''

    return cstr(emp_nm)  
  
  def get_approver_lst(self):
    approver_lst =[]
    approver_lst1 = get_obj('Authorization Control').get_approver_name(self.doc.doctype,0,self)
    if approver_lst1:
      approver_lst=approver_lst1
    else:
      approver_lst = [x[0] for x in sql("select distinct name from `tabProfile` where enabled=1 and name!='Administrator' and name!='Guest' and docstatus!=2")]
    return approver_lst

  def set_approver(self):
    ret={}
    approver_lst =[]
    emp_nm = self.get_employee_name()
    approver_lst = self.get_approver_lst()    
    ret = {'app_lst':"\n" + "\n".join(approver_lst), 'emp_nm':cstr(emp_nm)}
    return ret

  def update_voucher(self):
    sql("delete from `tabExpense Voucher Detail` where parent = '%s'"%self.doc.name)
    for d in getlist(self.doclist, 'expense_voucher_details'):
      if not d.expense_type or not d.claim_amount:
        msgprint("Please remove the extra blank row added")
        raise Exception
      d.save(1)
    if self.doc.total_sanctioned_amount:
      set(self.doc,'total_sanctioned_amount',self.doc.total_sanctioned_amount)
    if self.doc.remark:
      set(self.doc, 'remark', self.doc.remark)
  
  def approve_voucher(self):
    for d in getlist(self.doclist, 'expense_voucher_details'):
      if not d.sanctioned_amount:
        msgprint("Please add 'Sanctioned Amount' for all expenses")
        return cstr('Incomplete')
    
    if not self.doc.total_sanctioned_amount:
      msgprint("Please calculate total sanctioned amount using button 'Calculate Total Amount'")
      return cstr('No Amount')
    self.update_voucher()
    
    set(self.doc, 'approval_status', 'Approved')    
    # on approval notification
    get_obj('Notification Control').notify_contact('Expense Voucher Approved', self.doc.doctype, self.doc.name, self.doc.email_id, self.doc.employee_name)

    return cstr('Approved')
  
  def reject_voucher(self):
    
    if self.doc.remark:
      set(self.doc, 'remark', self.doc.remark)   
    set(self.doc, 'approval_status', 'Rejected')    

    # on approval notification
    get_obj('Notification Control').notify_contact('Expense Voucher Rejected', self.doc.doctype, self.doc.name, self.doc.email_id, self.doc.employee_name)

    return cstr('Rejected')
  
  def validate_curr_exp(self):
    for d in getlist(self.doclist, 'expense_voucher_details'):
      if flt(d.sanctioned_amount) > 0:
        if self.doc.approval_status == 'Draft':
          msgprint("Sanctioned amount can be added by Approver person only for submitted Expense Voucher")
          raise Exception
        elif self.doc.approval_status == 'Submitted' and session['user'] != self.doc.exp_approver:
          msgprint("Sanctioned amount can be added only by expense voucher Approver")
          raise Exception
  
  def validate_fiscal_year(self):
    fy=sql("select year_start_date from `tabFiscal Year` where name='%s'"%self.doc.fiscal_year)
    ysd=fy and fy[0][0] or ""
    yed=add_days(str(ysd),365)
    if str(self.doc.posting_date) < str(ysd) or str(self.doc.posting_date) > str(yed):
      msgprint("Posting Date is not within the Fiscal Year selected")
      raise Exception
    
  def validate(self):
    self.validate_curr_exp()
    self.validate_fiscal_year()
  
  def on_update(self):
    set(self.doc, 'approval_status', 'Draft')
  
  def validate_exp_details(self):
    if not getlist(self.doclist, 'expense_voucher_details'):
      msgprint("Please add expense voucher details")
      raise Exception
    
    if not self.doc.total_claimed_amount:
      msgprint("Please calculate Total Claimed Amount")
      raise Exception
    
    if not self.doc.exp_approver:
      msgprint("Please select Expense Voucher approver")
      raise Exception
  
  def validate_approver(self):
    app_lst = self.get_approver_lst()
    if self.doc.exp_approver and self.doc.exp_approver not in app_lst:
      msgprint("Approver "+self.doc.exp_approver+" is not authorized to approve this expense voucher. Please select another approver")
      valid_app = 'No'
    else:
      valid_app = 'Yes'
    ret = {'app_lst':("\n" + "\n".join(app_lst)), 'valid_approver':valid_app}
    return ret
  
  def on_submit(self):
    self.validate_exp_details()
    set(self.doc, 'approval_status', 'Submitted')
  
  def on_cancel(self):
    set(self.doc, 'approval_status', 'Cancelled')