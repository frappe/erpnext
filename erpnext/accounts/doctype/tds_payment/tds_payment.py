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
  def __init__(self,d,dl):
    self.doc, self.doclist = d, dl

  def autoname(self):
    self.doc.name = make_autoname(self.doc.naming_series+'.####')

  # Get pan and tan no from company
  #---------------------------------
  def get_registration_details(self):
    comp_det=sql("Select registration_details from `tabCompany` where name = '%s'"%(self.doc.company))
    if not comp_det:
      msgprint("Registration Details is not mentioned in comapny")
      ret = {'registration_details':  ''}
    else:
      ret = { 'registration_details': cstr(comp_det[0][0])}
   
    return ret

  # Get default bank and tds account
  #------------------------------------
  def get_bank_and_tds_account(self):
    tds_account=sql("Select account_head from `tabTDS Category Account` where parent='%s' and company='%s'"%(self.doc.tds_category,self.doc.company))
    tds_account = tds_account and tds_account[0][0] or ''

    def_bank = sql("select default_bank_account from tabCompany where name = '%s'" % self.doc.company)
    def_bank = def_bank and def_bank[0][0] or ''

    ret = {'tds_account':tds_account, 'bank_account': def_bank}
    return ret

  # Fetch voucherwise tds details
  #-------------------------------
  def get_tds_list(self):
    self.doc.clear_table(self.doclist,'tds_payment_details')
    self.doc.total_tds = 0
    import datetime
    if not self.doc.tds_category:
      msgprint("Please select tds category")
    else:
      if not self.doc.from_date or not self.doc.to_date:
        msgprint("Please enter from date and to date")
      else:
        idx = 1
        pv_det= sql("Select name,credit_to,grand_total,posting_date, ded_amount from `tabPayable Voucher` where tds_category='%s' And posting_date>= '%s' And posting_date <='%s'  and docstatus=1 and ded_amount > 0 Order By posting_date"%(self.doc.tds_category,self.doc.from_date,self.doc.to_date))
        if pv_det:
          idx = self.make_tds_table(pv_det, idx)
        
        jv_det= sql("Select name, supplier_account, total_debit,posting_date, ded_amount from `tabJournal Voucher` where tds_category='%s' And posting_date<= '%s' And posting_date >='%s' And docstatus=1 and ded_amount > 0 Order By posting_date"%(self.doc.tds_category,self.doc.to_date,self.doc.from_date))
        if jv_det:
          self.make_tds_table(jv_det, idx)

  # Create TDS table
  #------------------
  def make_tds_table(self,det, idx):
    for v in det:
      if not sql("select name from `tabTDS Payment Detail` where voucher_no = '%s' and parent != '%s' and docstatus = 1" % (v[0], self.doc.name)):
        child = addchild(self.doc, 'tds_payment_details', 'TDS Payment Detail', 1, self.doclist)
        child.voucher_no = v and v[0] or ''
        child.party_name = v and v[1] or ''
        child.amount_paid = v and flt(v[2]) or ''
        child.date_of_payment =v and v[3].strftime('%Y-%m-%d') or ''
        child.tds_amount = v and flt(v[4]) or 0
        child.cess_on_tds = 0
        child.total_tax_amount = child.tds_amount + child.cess_on_tds
        child.idx=idx
        idx=idx+1
        self.doc.total_tds= flt(self.doc.total_tds)+flt(child.total_tax_amount)
    return idx


  # Update acknowledgement details
  #---------------------------------------
  def update_ack_details(self):
    sql("update `tabTDS Payment` set cheque_no = '%s', bsr_code = '%s', date_of_receipt = '%s', challan_id = '%s' where name = '%s'" % (self.doc.cheque_no, self.doc.bsr_code, self.doc.date_of_receipt, self.doc.challan_id, self.doc.name))

  # Validate
  #------------------
  def validate(self):
    if self.doc.amended_from and not self.doc.amendment_date:
      msgprint("Please Enter Amendment Date")
      raise Exception

    self.calculate_total_tds()

  def calculate_total_tds(self):
    total = 0
    for d in getlist(self.doclist,'tds_payment_details'):
      total = flt(total)+flt(d.total_tax_amount)
    self.doc.total_tds = total
