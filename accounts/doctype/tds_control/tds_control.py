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


  # ============TDS==================
  # Stop payable voucher on which tds is applicable is made before posting date of the
  # voucher in which tds was applicable for 1st time
        
  def validate_first_entry(self,obj):
    if obj.doc.doctype == 'Payable Voucher':
      supp_acc = obj.doc.credit_to
    elif obj.doc.doctype == 'Journal Voucher':
      supp_acc = obj.doc.supplier_account

    if obj.doc.ded_amount:
      # first pv
      first_pv = sql("select posting_date from `tabPayable Voucher` where credit_to = '%s' and docstatus = 1 and tds_category = '%s' and fiscal_year = '%s' and tds_applicable = 'Yes' and (ded_amount != 0 or ded_amount is not null) order by posting_date asc limit 1"%(supp_acc, obj.doc.tds_category, obj.doc.fiscal_year))
      first_pv_date = first_pv and first_pv[0][0] or ''
      # first jv
      first_jv = sql("select posting_date from `tabJournal Voucher` where supplier_account = '%s'and docstatus = 1 and tds_category = '%s' and fiscal_year = '%s' and tds_applicable = 'Yes' and (ded_amount != 0 or ded_amount is not null) order by posting_date asc limit 1"%(supp_acc, obj.doc.tds_category, obj.doc.fiscal_year))
      first_jv_date = first_jv and first_jv[0][0] or ''

      #first tds voucher date
      first_tds_date = ''
      if first_pv_date and first_jv_date:
        first_tds_date = first_pv_date < first_jv_date and first_pv_date or first_jv_date
      elif first_pv_date:
        first_tds_date = first_pv_date
      elif first_jv_date:
        first_tds_date = first_jv_date

      if first_tds_date and getdate(obj.doc.posting_date) < first_tds_date:
        msgprint("First tds voucher for this category has been made already. Hence payable voucher cannot be made before posting date of first tds voucher ")
        raise Exception
    
  # TDS function definition
  #---------------------------
  def get_tds_amount(self, obj):    
    # Validate if posting date b4 first tds entry for this category
    self.validate_first_entry(obj)

    # get current amount and supplier head
    if obj.doc.doctype == 'Payable Voucher':
      supplier_account = obj.doc.credit_to
      total_amount=flt(obj.doc.grand_total)
      for d in getlist(obj.doclist,'advance_allocation_details'):
        if flt(d.tds_amount)!=0:
          total_amount -= flt(d.allocated_amount)
    elif obj.doc.doctype == 'Journal Voucher':      
      supplier_account = obj.doc.supplier_account
      total_amount = obj.doc.total_debit

    if obj.doc.tds_category:      
      # get total billed
      total_billed = 0
      pv = sql("select sum(ifnull(grand_total,0)), sum(ifnull(ded_amount,0)) from `tabPayable Voucher` where tds_category = %s and credit_to = %s and fiscal_year = %s and docstatus = 1 and name != %s and is_opening != 'Yes'", (obj.doc.tds_category, supplier_account, obj.doc.fiscal_year, obj.doc.name))
      jv = sql("select sum(ifnull(total_debit,0)), sum(ifnull(ded_amount,0)) from `tabJournal Voucher` where tds_category = %s and supplier_account = %s and fiscal_year = %s and docstatus = 1 and name != %s and is_opening != 'Yes'", (obj.doc.tds_category, supplier_account, obj.doc.fiscal_year, obj.doc.name))
      tds_in_pv = pv and pv[0][1] or 0
      tds_in_jv = jv and jv[0][1] or 0
      total_billed += flt(pv and pv[0][0] or 0)+flt(jv and jv[0][0] or 0)+flt(total_amount)
      
      # get slab
      slab = sql("SELECT * FROM `tabTDS Rate Detail` t1, `tabTDS Rate Chart` t2 WHERE t1.category = '%s' AND t1.parent=t2.name and t2.applicable_from <= '%s' ORDER BY t2.applicable_from DESC LIMIT 1" % (obj.doc.tds_category, obj.doc.posting_date), as_dict = 1)

      if slab and flt(slab[0]['slab_from']) <= total_billed:

        if flt(tds_in_pv) <= 0 and flt(tds_in_jv) <= 0:
          total_amount = total_billed
        slab = slab[0]
        # special tds rate
        special_tds = sql("select special_tds_rate, special_tds_limit, special_tds_rate_applicable from `tabTDS Detail` where parent = '%s' and tds_category = '%s'"% (supplier_account,obj.doc.tds_category))

        # get_pan_number
        pan_no = sql("select pan_number from `tabAccount` where name = '%s'" % supplier_account)
        pan_no = pan_no and cstr(pan_no[0][0]) or ''
        if not pan_no and flt(slab.get('rate_without_pan')):
          msgprint("As there is no PAN number mentioned in the account head: %s, TDS amount will be calculated at rate %s%%" % (supplier_account, cstr(slab['rate_without_pan'])))
          tds_rate = flt(slab.get('rate_without_pan'))
        elif special_tds and special_tds[0][2]=='Yes' and (flt(special_tds[0][1])==0 or flt(special_tds[0][1]) >= flt(total_amount)):
          tds_rate =  flt(special_tds[0][0])
        else: 
          tds_rate=flt(slab['rate'])
        # calculate tds amount
        if flt(slab['rate']):
          ac = sql("SELECT account_head FROM `tabTDS Category Account` where parent=%s and company=%s", (obj.doc.tds_category,obj.doc.company))

          if ac:
            obj.doc.tax_code = ac[0][0]
            obj.doc.rate = tds_rate
            obj.doc.ded_amount = round(flt(tds_rate) * flt(total_amount) / 100)
          else:
            msgprint("TDS Account not selected in TDS Category %s" % (obj.doc.tds_category))
            raise Exception
