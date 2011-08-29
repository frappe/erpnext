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
    self.defaults = get_defaults()
    self.tname = 'PO Detail'
    self.fname = 'po_details'

  # Autoname
  # ---------
  def autoname(self):
    self.doc.name = make_autoname(self.doc.naming_series+'.#####')

  def get_default_schedule_date(self):
    get_obj(dt = 'Purchase Common').get_default_schedule_date(self)
    
  def validate_fiscal_year(self):
    get_obj(dt = 'Purchase Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.transaction_date,'PO Date')


  # Get Item Details
  def get_item_details(self, arg =''):
    return get_obj(dt='Purchase Common').get_item_details(self,arg)

  # Get UOM Details
  def get_uom_details(self, arg = ''):
    return get_obj(dt='Purchase Common').get_uom_details(arg)

  # get available qty at warehouse
  def get_bin_details(self, arg = ''):
    return get_obj(dt='Purchase Common').get_bin_details(arg)

  # Pull Indent
  def get_indent_details(self):
    #self.validate_prev_docname() 
    if self.doc.indent_no:
      get_obj('DocType Mapper','Indent-Purchase Order').dt_map('Indent','Purchase Order',self.doc.indent_no, self.doc, self.doclist, "[['Indent','Purchase Order'],['Indent Detail', 'PO Detail']]")
      for d in getlist(self.doclist, 'po_details'):			
        if d.item_code:
          item = sql("select last_purchase_rate from tabItem where name = '%s'" %(d.item_code), as_dict=1)
          d.purchase_rate = item and flt(item[0]['last_purchase_rate']) or 0
          d.import_rate = flt(item and flt(item[0]['last_purchase_rate']) or 0) / flt(self.doc.fields.has_key('conversion_rate') and flt(self.doc.conversion_rate) or 1)
    if self.doc.supplier_qtn:
      get_obj('DocType Mapper','Supplier Quotation-Purchase Order').dt_map('Supplier Quotation','Purchase Order',self.doc.supplier_qtn, self.doc, self.doclist, "[['Supplier Quotation','Purchase Order'],['Supplier Quotation Detail', 'PO Detail']]")
  
  # GET TERMS & CONDITIONS
  # =====================================================================================
  def get_tc_details(self):
    return get_obj('Purchase Common').get_tc_details(self)

  # validate if indent has been pulled twice
  def validate_prev_docname(self):
    for d in getlist(self.doclist, 'po_details'): 
      if d.prevdoc_docname and self.doc.indent_no == d.prevdoc_docname:
        msgprint(cstr(self.doc.indent_no) + " indent details have already been pulled. ")
        raise Exception

  # get last purchase rate
  def get_last_purchase_rate(self):
    get_obj('Purchase Common').get_last_purchase_rate(self)
    
  # validation
  #-------------------------------------------------------------------------------------------------------------
  def validate_doc(self,pc_obj):
    # Please Check Supplier Quotation - Purchase ORder Transaction , it has to be discussed
    if self.doc.supp_quo_no:
      pc_obj.validate_doc(obj = self, prevdoc_doctype = 'Supplier Quotation', prevdoc_docname = cstr(self.doc.supp_quo_no))
    else:
      # Validate values with reference document
      pc_obj.validate_reference_value(obj = self)

  # Check for Stopped status 
  def check_for_stopped_status(self, pc_obj):
    check_list =[]
    for d in getlist(self.doclist, 'po_details'):
      if d.fields.has_key('prevdoc_docname') and d.prevdoc_docname and d.prevdoc_docname not in check_list:
        check_list.append(d.prevdoc_docname)
        pc_obj.check_for_stopped_status( d.prevdoc_doctype, d.prevdoc_docname)

    
  # Validate
  def validate(self):
    self.validate_fiscal_year()
    # Step 1:=> set status as "Draft"
    set(self.doc, 'status', 'Draft')
    
    # Step 2:=> get Purchase Common Obj
    pc_obj = get_obj(dt='Purchase Common')
    
    # Step 3:=> validate mandatory
    pc_obj.validate_mandatory(self)

    # Step 4:=> validate for items
    pc_obj.validate_for_items(self)

    # Step 5:=> validate conversion rate
    pc_obj.validate_conversion_rate(self)
    
    # Get po date
    pc_obj.get_prevdoc_date(self)
    
    # validate_doc
    self.validate_doc(pc_obj)
    
    # Check for stopped status
    self.check_for_stopped_status(pc_obj)
    
      
     # get total in words
    dcc = TransactionBase().get_company_currency(self.doc.company)
    self.doc.in_words = pc_obj.get_total_in_words(dcc, self.doc.grand_total)
    self.doc.in_words_import = pc_obj.get_total_in_words(self.doc.currency, self.doc.grand_total_import)
  
  # update bin
  # ----------
  def update_bin(self, is_submit, is_stopped = 0):
    pc_obj = get_obj('Purchase Common')
    for d in getlist(self.doclist, 'po_details'):
      #1. Check if is_stock_item == 'Yes'
      if sql("select is_stock_item from tabItem where name=%s", d.item_code)[0][0]=='Yes':
        
        ind_qty, po_qty = 0, flt(d.qty) * flt(d.conversion_factor)
        if is_stopped:
          po_qty = flt(d.qty) > flt(d.received_qty) and flt( flt(flt(d.qty) - flt(d.received_qty)) * flt(d.conversion_factor))or 0 
        
        # No updates in Indent on Stop / Unstop
        if cstr(d.prevdoc_doctype) == 'Indent' and not is_stopped:
          # get qty and pending_qty of prevdoc 
          curr_ref_qty = pc_obj.get_qty( d.doctype, 'prevdoc_detail_docname', d.prevdoc_detail_docname, 'Indent Detail', 'Indent - Purchase Order', self.doc.name)
          max_qty, qty, curr_qty = flt(curr_ref_qty.split('~~~')[1]), flt(curr_ref_qty.split('~~~')[0]), 0
          
          if flt(qty) + flt(po_qty) > flt(max_qty):
            curr_qty = flt(max_qty) - flt(qty)
            # special case as there is no restriction for Indent - Purchase Order 
            curr_qty = (curr_qty > 0) and curr_qty or 0
          else:
            curr_qty = flt(po_qty)
          
          ind_qty = -flt(curr_qty)

        #==> Update Bin's Indent Qty by +- ind_qty and Ordered Qty by +- qty
        get_obj('Warehouse', d.warehouse).update_bin(0, 0, (is_submit and 1 or -1) * flt(po_qty), (is_submit and 1 or -1) * flt(ind_qty), 0, d.item_code, self.doc.transaction_date)

  def check_modified_date(self):
    mod_db = sql("select modified from `tabPurchase Order` where name = '%s'" % self.doc.name)
    date_diff = sql("select TIMEDIFF('%s', '%s')" % ( mod_db[0][0],cstr(self.doc.modified)))
    
    if date_diff and date_diff[0][0]:
      msgprint(cstr(self.doc.doctype) +" => "+ cstr(self.doc.name) +" has been modified. Please Refresh. ")
      raise Exception

  # On Close
  #-------------------------------------------------------------------------------------------------
  def update_status(self, status):
    self.check_modified_date()
    # step 1:=> Set Status
    set(self.doc,'status',cstr(status))

    # step 2:=> Update Bin
    self.update_bin(is_submit = (status == 'Submitted') and 1 or 0, is_stopped = 1)

    # step 3:=> Acknowledge user
    msgprint(self.doc.doctype + ": " + self.doc.name + " has been %s." % ((status == 'Submitted') and 'Unstopped' or cstr(status)))


  # On Submit
  def on_submit(self):
    pc_obj = get_obj(dt ='Purchase Common')
    
    # Step 1 :=> Update Previous Doc i.e. update pending_qty and Status accordingly
    pc_obj.update_prevdoc_detail(self, is_submit = 1)

    # Step 2 :=> Update Bin 
    self.update_bin(is_submit = 1, is_stopped = 0)
    
    # Step 3 :=> Check For Approval Authority
    get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total)
    
    # Step 4 :=> Update Current PO No. in Supplier as last_purchase_order.
    update_supplier = sql("update `tabSupplier` set last_purchase_order = '%s' where name = '%s'" % (self.doc.name, self.doc.supplier))

    # Step 5 :=> Update last purchase rate
    pc_obj.update_last_purchase_rate(self, is_submit = 1)

    # Step 6 :=> Set Status
    set(self.doc,'status','Submitted')
    
    self.doc.indent_no = '';
  
    # on submit notification
    get_obj('Notification Control').notify_contact('Purchase Order', self.doc.doctype,self.doc.name, self.doc.email_id, self.doc.contact_person)
   
  # On Cancel
  # -------------------------------------------------------------------------------------------------------
  def on_cancel(self):
    pc_obj = get_obj(dt = 'Purchase Common')
    
    # 1.Check if PO status is stopped
    pc_obj.check_for_stopped_status(cstr(self.doc.doctype), cstr(self.doc.name))
    
    self.check_for_stopped_status(pc_obj)
    
    # 2.Check if Purchase Receipt has been submitted against current Purchase Order
    pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Receipt', docname = self.doc.name, detail_doctype = 'Purchase Receipt Detail')

    # 3.Check if Payable Voucher has been submitted against current Purchase Order
    #pc_obj.check_docstatus(check = 'Next', doctype = 'Payable Voucher', docname = self.doc.name, detail_doctype = 'PV Detail')
    
    submitted = sql("select t1.name from `tabPayable Voucher` t1,`tabPV Detail` t2 where t1.name = t2.parent and t2.purchase_order = '%s' and t1.docstatus = 1" % self.doc.name)
    if submitted:
      msgprint("Purchase Invoice : " + cstr(submitted[0][0]) + " has already been submitted !")
      raise Exception

    # 4.Set Status as Cancelled
    set(self.doc,'status','Cancelled')

    # 5.Update Indents Pending Qty and accordingly it's Status 
    pc_obj.update_prevdoc_detail(self,is_submit = 0)
    
    # 6.Update Bin  
    self.update_bin( is_submit = 0, is_stopped = 0)
    
    # Step 7 :=> Update last purchase rate 
    pc_obj.update_last_purchase_rate(self, is_submit = 0)
    
#----------- code for Sub-contracted Items -------------------
  #--------check for sub-contracted items and accordingly update PO raw material detail table--------
  def update_rw_material_detail(self):
    for d in getlist(self.doclist,'po_details'):
      item_det = sql("select is_sub_contracted_item, is_purchase_item from `tabItem` where name = '%s'"%(d.item_code))
      
      if item_det[0][0] == 'Yes':
        if item_det[0][1] == 'Yes':
          if not self.doc.is_subcontracted:
            msgprint("Please enter whether purchase order to be made for subcontracting or for purchasing in 'Is Subcontracted' field .")
            raise Exception
          if self.doc.is_subcontracted == 'Yes':
            self.add_bom(d)
          else:
            self.doc.clear_table(self.doclist,'po_raw_material_details',1)
            self.doc.save()
        elif item_det[0][1] == 'No':
          self.add_bom(d)
        
      self.delete_irrelevant_raw_material()
      #---------------calculate amt in  PO Raw Material Detail-------------
      self.calculate_amount(d)
      
  def add_bom(self, d):
    #----- fetching default bom from Bill of Materials instead of Item Master --
    bom_det = sql("select t1.item, t2.item_code, t2.qty_consumed_per_unit, t2.moving_avg_rate, t2.value_as_per_mar, t2.stock_uom, t2.name, t2.parent from `tabBill Of Materials` t1, `tabBOM Material` t2 where t2.parent = t1.name and t1.item = '%s' and ifnull(t1.is_default,0) = 1 and t1.docstatus = 1" % d.item_code)
    
    if not bom_det:
      msgprint("No default BOM exists for item: %s" % d.item_code)
      raise Exception
    else:
      #-------------- add child function--------------------
      chgd_rqd_qty = []
      for i in bom_det:
        if i and not sql("select name from `tabPO Raw Material Detail` where reference_name = '%s' and bom_detail_no = '%s' and parent = '%s' " %(d.name, i[6], self.doc.name)):

          rm_child = addchild(self.doc, 'po_raw_material_details', 'PO Raw Material Detail', 1, self.doclist)

          rm_child.reference_name = d.name
          rm_child.bom_detail_no = i and i[6] or ''
          rm_child.main_item_code = i and i[0] or ''
          rm_child.rm_item_code = i and i[1] or ''
          rm_child.stock_uom = i and i[5] or ''
          rm_child.rate = i and flt(i[3]) or flt(i[4])
          rm_child.conversion_factor = d.conversion_factor
          rm_child.required_qty = flt(i  and flt(i[2]) or 0) * flt(d.qty) * flt(d.conversion_factor)
          rm_child.amount = flt(flt(rm_child.consumed_qty)*flt(rm_child.rate))
          rm_child.save()
          chgd_rqd_qty.append(cstr(i[1]))
        else:
          act_qty = flt(i  and flt(i[2]) or 0) * flt(d.qty) * flt(d.conversion_factor)
          for po_rmd in getlist(self.doclist, 'po_raw_material_details'):
            if i and i[6] == po_rmd.bom_detail_no and (flt(act_qty) != flt(po_rmd.required_qty) or i[1] != po_rmd.rm_item_code):
              chgd_rqd_qty.append(cstr(i[1]))
              po_rmd.main_item_code = i[0]
              po_rmd.rm_item_code = i[1]
              po_rmd.stock_uom = i[5]
              po_rmd.required_qty = flt(act_qty)
              po_rmd.rate = i and flt(i[3]) or flt(i[4])
              po_rmd.amount = flt(flt(po_rmd.consumed_qty)*flt(po_rmd.rate))
              

  # Delete irrelevant raw material from PR Raw material details
  #--------------------------------------------------------------  
  def delete_irrelevant_raw_material(self):
    for d in getlist(self.doclist,'po_raw_material_details'):
      if not sql("select name from `tabPO Detail` where name = '%s' and parent = '%s'and item_code = '%s'" % (d.reference_name, self.doc.name, d.main_item_code)):
        d.parent = 'old_par:'+self.doc.name
        d.save()
    
  def calculate_amount(self, d):
    amt = 0
    for i in getlist(self.doclist,'po_raw_material_details'):
      
      if(i.reference_name == d.name):
        i.amount = flt(i.required_qty)* flt(i.rate)
        amt += i.amount
    d.rm_supp_cost = amt

  # On Update
  # ----------------------------------------------------------------------------------------------------    
  def on_update(self):
    self.update_rw_material_detail()
    

# OTHER CHARGES TRIGGER FUNCTIONS
# ====================================================================================
  
  # *********** Get Tax rate if account type is TAX ********************
  def get_rate(self,arg):
    return get_obj('Purchase Common').get_rate(arg,self)

  # **** Pull details from other charges master (Get Other Charges) ****
  def get_purchase_tax_details(self):
    return get_obj('Purchase Common').get_purchase_tax_details(self)

  # Repair Purchase Order
  # ===========================================
  def repair_purchase_order(self):
    get_obj('Purchase Common', 'Purchase Common').repair_curr_doctype_details(self)
