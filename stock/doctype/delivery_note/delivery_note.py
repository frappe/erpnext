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
    self.tname = 'Delivery Note Detail'
    self.fname = 'delivery_note_details'

    # Notification objects
    self.notify_obj = get_obj('Notification Control')

  # Autoname
  # ---------
  def autoname(self):
    self.doc.name = make_autoname(self.doc.naming_series+'.#####')


# DOCTYPE TRIGGERS FUNCTIONS
# ==============================================================================
#************Fiscal Year Validation*****************************
  def validate_fiscal_year(self):
    get_obj('Sales Common').validate_fiscal_year(self.doc.fiscal_year,self.doc.posting_date,'Posting Date')


  # ****** Get contact person details based on customer selected ****
  def get_contact_details(self):
    return get_obj('Sales Common').get_contact_details(self,0)

  # *********** Get Commission rate of Sales Partner ****************
  def get_comm_rate(self, sales_partner):
    return get_obj('Sales Common').get_comm_rate(sales_partner, self)

  # *************** Pull Sales Order Details ************************
  def pull_sales_order_details(self):
    self.validate_prev_docname()
    self.doc.clear_table(self.doclist,'other_charges')

    if self.doc.sales_order_no:
      get_obj('DocType Mapper', 'Sales Order-Delivery Note').dt_map('Sales Order', 'Delivery Note', self.doc.sales_order_no, self.doc, self.doclist, "[['Sales Order', 'Delivery Note'],['Sales Order Detail', 'Delivery Note Detail'],['RV Tax Detail','RV Tax Detail'],['Sales Team','Sales Team']]")
    else:
      msgprint("Please select Sales Order No. whose details need to be pulled")

    return cstr(self.doc.sales_order_no)



  #-------------------set item details -uom and item group----------------
  def set_item_details(self):
    for d in getlist(self.doclist,'delivery_note_details'):
      res = sql("select stock_uom, item_group from `tabItem` where name ='%s'"%d.item_code)
      if not d.stock_uom:    d.stock_uom = res and cstr(res[0][0]) or ''
      if not d.item_group:   d.item_group = res and cstr(res[0][1]) or ''
      d.save()

  # ::::: Validates that Sales Order is not pulled twice :::::::
  def validate_prev_docname(self):
    for d in getlist(self.doclist, 'delivery_note_details'):
      if self.doc.sales_order_no == d.prevdoc_docname:
        msgprint(cstr(self.doc.sales_order_no) + " sales order details have already been pulled. ")
        raise Exception, "Validation Error. "

  #Set Actual Qty based on item code and warehouse
  #------------------------------------------------------
  def set_actual_qty(self):
    for d in getlist(self.doclist, 'delivery_note_details'):
      if d.item_code and d.warehouse:
        actual_qty = sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (d.item_code, d.warehouse))
        d.actual_qty = actual_qty and flt(actual_qty[0][0]) or 0


  # GET TERMS & CONDITIONS
  # -------------------------------------
  def get_tc_details(self):
    return get_obj('Sales Common').get_tc_details(self)

  #pull project customer
  #-------------------------
  def pull_project_customer(self):
    res = sql("select customer from `tabProject` where name = '%s'"%self.doc.project_name)
    if res:
      get_obj('DocType Mapper', 'Project-Delivery Note').dt_map('Project', 'Delivery Note', self.doc.project_name, self.doc, self.doclist, "[['Project', 'Delivery Note']]")

# DELIVERY NOTE DETAILS TRIGGER FUNCTIONS
# ================================================================================

  # ***************** Get Item Details ******************************
  def get_item_details(self, item_code):
    return get_obj('Sales Common').get_item_details(item_code, self)

  # *** Re-calculates Basic Rate & amount based on Price List Selected ***
  def get_adj_percent(self, arg=''):
    get_obj('Sales Common').get_adj_percent(self)

  # ********** Get Actual Qty of item in warehouse selected *************
  def get_actual_qty(self,args):
    args = eval(args)
    actual_qty = sql("select actual_qty from `tabBin` where item_code = '%s' and warehouse = '%s'" % (args['item_code'], args['warehouse']), as_dict=1)
    ret = {
       'actual_qty' : actual_qty and flt(actual_qty[0]['actual_qty']) or 0
    }
    return ret


# OTHER CHARGES TRIGGER FUNCTIONS
# ====================================================================================

  # *********** Get Tax rate if account type is TAX ********************
  def get_rate(self,arg):
    return get_obj('Sales Common').get_rate(arg)

  # Load Default Charges
  # ----------------------------------------------------------
  def load_default_taxes(self):
    return get_obj('Sales Common').load_default_taxes(self)


  # **** Pull details from other charges master (Get Other Charges) ****
  def get_other_charges(self):
    return get_obj('Sales Common').get_other_charges(self)


  #check in manage account if sales order required or not.
  # ====================================================================================
  def so_required(self):
    res = sql("select value from `tabSingles` where doctype = 'Manage Account' and field = 'so_required'")
    if res and res[0][0] == 'Yes':
       for d in getlist(self.doclist,'delivery_note_details'):
         if not d.prevdoc_docname:
           msgprint("Sales Order No. required against item %s"%d.item_code)
           raise Exception



# VALIDATE
# ====================================================================================
  def validate(self):
    self.so_required()
    self.validate_fiscal_year()
    self.validate_proj_cust()
    sales_com_obj = get_obj(dt = 'Sales Common')
    sales_com_obj.check_stop_sales_order(self)
    sales_com_obj.check_active_sales_items(self)
    sales_com_obj.get_prevdoc_date(self)
    self.validate_mandatory()
    #self.validate_prevdoc_details()
    self.validate_reference_value()
    self.validate_for_items()
    sales_com_obj.make_packing_list(self,'delivery_note_details')
    get_obj('Stock Ledger').validate_serial_no(self, 'packing_details')
    sales_com_obj.validate_max_discount(self, 'delivery_note_details')             #verify whether rate is not greater than max discount
    sales_com_obj.get_allocated_sum(self)  # this is to verify that the allocated % of sales persons is 100%
    sales_com_obj.check_conversion_rate(self)
    # ::::::: Get total in Words ::::::::
    dcc = TransactionBase().get_company_currency(self.doc.company)
    self.doc.in_words = sales_com_obj.get_total_in_words(dcc, self.doc.rounded_total)
    self.doc.in_words_export = sales_com_obj.get_total_in_words(self.doc.currency, self.doc.rounded_total_export)

    # ::::::: Set actual qty for each item in selected warehouse :::::::
    self.update_current_stock()
    # :::::: set DN status :::::::

    self.doc.status = 'Draft'
    if not self.doc.billing_status: self.doc.billing_status = 'Not Billed'
    if not self.doc.installation_status: self.doc.installation_status = 'Not Installed'


  # ************** Validate Mandatory *************************
  def validate_mandatory(self):
    # :::::::::: Amendment Date ::::::::::::::
    if self.doc.amended_from and not self.doc.amendment_date:
      msgprint("Please Enter Amendment Date")
      raise Exception, "Validation Error. "

  #check for does customer belong to same project as entered..
  #-------------------------------------------------------------------------------------------------
  def validate_proj_cust(self):
    if self.doc.project_name and self.doc.customer:
      res = sql("select name from `tabProject` where name = '%s' and (customer = '%s' or ifnull(customer,'')='')"%(self.doc.project_name, self.doc.customer))
      if not res:
        msgprint("Customer - %s does not belong to project - %s. \n\nIf you want to use project for multiple customers then please make customer details blank in project - %s."%(self.doc.customer,self.doc.project_name,self.doc.project_name))
        raise Exception

  # Validate values with reference document
  #----------------------------------------
  def validate_reference_value(self):
    get_obj('DocType Mapper', 'Sales Order-Delivery Note', with_children = 1).validate_reference_value(self, self.doc.name)


  # ******* Validate Previous Document Details ************
  def validate_prevdoc_details(self):
    for d in getlist(self.doclist,'delivery_note_details'):

      prevdoc = d.prevdoc_doctype
      prevdoc_docname = d.prevdoc_docname

      if prevdoc_docname and prevdoc:
        # ::::::::::: Validates Transaction Date of DN and previous doc (i.e. SO , PO, PR) *********
        trans_date = sql("select transaction_date from `tab%s` where name = '%s'" %(prevdoc,prevdoc_docname))[0][0]
        if trans_date and getdate(self.doc.transaction_date) < (trans_date):
          msgprint("Your Voucher Date cannot be before "+cstr(prevdoc)+" Date.")
          raise Exception
        # ::::::::: Validates DN and previous doc details ::::::::::::::::::
        get_name = sql("select name from `tab%s` where name = '%s'" % (prevdoc, prevdoc_docname))
        name = get_name and get_name[0][0] or ''
        if name:  #check for incorrect docname
          if prevdoc == 'Sales Order':
            dt = sql("select company, docstatus, customer, currency, sales_partner from `tab%s` where name = '%s'" % (prevdoc, name))
            cust_name = dt and dt[0][2] or ''
            if cust_name != self.doc.customer:
              msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " customer :" + cstr(cust_name) + " does not match with customer : " + cstr(self.doc.customer) + " of current document.")
              raise Exception, "Validation Error. "
            sal_partner = dt and dt[0][4] or ''
            if sal_partner != self.doc.sales_partner:
              msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " sales partner name :" + cstr(sal_partner) + " does not match with sales partner name : " + cstr(self.doc.sales_partner_name) + " of current document.")
              raise Exception, "Validation Error. "
          else:
            dt = sql("select company, docstatus, supplier, currency from `tab%s` where name = '%s'" % (prevdoc, name))
            supp_name = dt and dt[0][2] or ''
            company_name = dt and dt[0][0] or ''
            docstatus = dt and dt[0][1] or 0
            currency = dt and dt[0][3] or ''
            if (currency != self.doc.currency):
              msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " currency : "+ cstr(currency) + "does not match with Currency: " + cstr(self.doc.currency) + "of current document")
              raise Exception, "Validation Error."
            if (company_name != self.doc.company):
              msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " does not belong to the Company: " + cstr(self.doc.company_name))
              raise Exception, "Validation Error."
            if (docstatus != 1):
              msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " is not Submitted Document.")
              raise Exception, "Validation Error."
        else:
          msgprint(cstr(prevdoc) + ": " + cstr(prevdoc_docname) + " is not a valid " + cstr(prevdoc))
          raise Exception, "Validation Error."


  # ******************** Validate Items **************************
  def validate_for_items(self):
    check_list, chk_dupl_itm = [], []
    for d in getlist(self.doclist,'delivery_note_details'):
      ch = sql("select is_stock_item from `tabItem` where name = '%s'"%d.item_code)
      if d.prevdoc_doctype and d.prevdoc_detail_docname and ch and ch[0][0]=='Yes':
        self.validate_items_with_prevdoc(d)

      # validates whether item is not entered twice
      e = [d.item_code, d.description, d.warehouse, d.prevdoc_docname or '', d.batch_no or '']
      f = [d.item_code, d.description, d.prevdoc_docname or '']

      if ch and ch[0][0] == 'Yes':
        if e in check_list:
          msgprint("Please check whether item %s has been entered twice wrongly." % d.item_code)
        else:
          check_list.append(e)
      elif ch and ch[0][0] == 'No':
        if f in chk_dupl_itm:
          msgprint("Please check whether item %s has been entered twice wrongly." % d.item_code)
        else:
          chk_dupl_itm.append(f)


  # check if same item, warehouse present in prevdoc
  # ------------------------------------------------------------------
  def validate_items_with_prevdoc(self, d):
    if d.prevdoc_doctype == 'Sales Order':
      data = sql("select item_code, reserved_warehouse from `tabSales Order Detail` where parent = '%s' and name = '%s'" % (d.prevdoc_docname, d.prevdoc_detail_docname))
    if d.prevdoc_doctype == 'Purchase Receipt':
      data = sql("select item_code, rejected_warehouse from `tabPurchase Receipt Detail` where parent = '%s' and name = '%s'" % (d.prevdoc_docname, d.prevdoc_detail_docname))
    if not data or data[0][0] != d.item_code or data[0][1] != d.warehouse:
      msgprint("Item: %s / Warehouse: %s is not matching with Sales Order: %s. Sales Order might be modified after fetching data from it. Please delete items and fetch again." % (d.item_code, d.warehouse, d.prevdoc_docname))
      raise Exception


  # ********* UPDATE CURRENT STOCK *****************************
  def update_current_stock(self):
    for d in getlist(self.doclist, 'delivery_note_details'):
      bin = sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
      d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0

    for d in getlist(self.doclist, 'packing_details'):
      bin = sql("select actual_qty, projected_qty from `tabBin` where item_code =  %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
      d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0
      d.projected_qty = bin and flt(bin[0]['projected_qty']) or 0


# ON SUBMIT
# =================================================================================================
  def on_submit(self):
    set(self.doc, 'message', 'Items against your Order #%s have been delivered. Delivery #%s: ' % (self.doc.po_no, self.doc.name))
    self.check_qty_in_stock()
    # Check for Approving Authority
    get_obj('Authorization Control').validate_approving_authority(self.doc.doctype, self.doc.company, self.doc.grand_total, self)
    sl_obj = get_obj("Stock Ledger")
    sl_obj.validate_serial_no_warehouse(self, 'packing_details')
    sl_obj.update_serial_record(self, 'packing_details', is_submit = 1, is_incoming = 0)
    get_obj("Sales Common").update_prevdoc_detail(1,self)
    self.update_stock_ledger(update_stock = 1)

    #------------Check Credit Limit---------------------
    self.credit_limit()

    # set DN status
    set(self.doc, 'status', 'Submitted')

    # on submit notification
    self.notify_obj.notify_contact('Delivery Note',self.doc.doctype,self.doc.name, self.doc.email_id, self.doc.contact_person)


  # *********** Checks whether actual quantity is present in warehouse *************
  def check_qty_in_stock(self):
    for d in getlist(self.doclist, 'packing_details'):
      is_stock_item = sql("select is_stock_item from `tabItem` where name = '%s'" % d.item_code)[0][0]
      if is_stock_item == 'Yes' and d.warehouse and flt(d.qty) > flt(d.actual_qty):
        msgprint("For Item: " + cstr(d.item_code) + " at Warehouse: " + cstr(d.warehouse) + " Quantity: " + cstr(d.qty) +" is not Available. (Must be less than or equal to " + cstr(d.actual_qty) + " )")
        raise Exception, "Validation Error"



# ON CANCEL
# =================================================================================================
  def on_cancel(self):
    sales_com_obj = get_obj(dt = 'Sales Common')
    sales_com_obj.check_stop_sales_order(self)
    self.check_next_docstatus()
    get_obj('Stock Ledger').update_serial_record(self, 'packing_details', is_submit = 0, is_incoming = 0)
    sales_com_obj.update_prevdoc_detail(0,self)
    self.update_stock_ledger(update_stock = -1)
    # :::::: set DN status :::::::
    set(self.doc, 'status', 'Cancelled')


  # ******************** Check Next DocStatus **************************
  def check_next_docstatus(self):
    submit_rv = sql("select t1.name from `tabReceivable Voucher` t1,`tabRV Detail` t2 where t1.name = t2.parent and t2.delivery_note = '%s' and t1.docstatus = 1" % (self.doc.name))
    if submit_rv:
      msgprint("Sales Invoice : " + cstr(submit_rv[0][0]) + " has already been submitted !")
      raise Exception , "Validation Error."

    submit_in = sql("select t1.name from `tabInstallation Note` t1, `tabInstalled Item Details` t2 where t1.name = t2.parent and t2.prevdoc_docname = '%s' and t1.docstatus = 1" % (self.doc.name))
    if submit_in:
      msgprint("Installation Note : "+cstr(submit_in[0][0]) +" has already been submitted !")
      raise Exception , "Validation Error."


# UPDATE STOCK LEDGER
# =================================================================================================
  def update_stock_ledger(self, update_stock, is_stopped = 0):
    self.values = []
    for d in self.get_item_list(is_stopped):
      stock_item = sql("SELECT is_stock_item, is_sample_item FROM tabItem where name = '%s'"%(d[1]), as_dict = 1) # stock ledger will be updated only if it is a stock item
      if stock_item[0]['is_stock_item'] == "Yes":
        if not d[0]:
          msgprint("Message: Please enter Warehouse for item %s as it is stock item."% d[1])
          raise Exception
        # if prevdoc_doctype = "Sales Order"
        if d[3] < 0 :
          # Reduce Reserved Qty from warehouse
          bin = get_obj('Warehouse', d[0]).update_bin(0, flt(update_stock) * flt(d[3]), 0, 0, 0, d[1], self.doc.transaction_date)

        # Reduce actual qty from warehouse
        self.make_sl_entry(d, d[0], - flt(d[2]) , 0, update_stock)
    get_obj('Stock Ledger', 'Stock Ledger').update_stock(self.values)


  # ***************** Gets Items from packing list *****************
  def get_item_list(self, is_stopped):
   return get_obj('Sales Common').get_item_list(self, is_stopped)


  # ********************** Make Stock Entry ************************************
  def make_sl_entry(self, d, wh, qty, in_value, update_stock):
    self.values.append({
      'item_code'           : d[1],
      'warehouse'           : wh,
      'transaction_date'    : self.doc.transaction_date,
      'posting_date'        : self.doc.posting_date,
      'posting_time'        : self.doc.posting_time,
      'voucher_type'        : 'Delivery Note',
      'voucher_no'          : self.doc.name,
      'voucher_detail_no'   : '',
      'actual_qty'          : qty,
      'stock_uom'           : d[4],
      'incoming_rate'       : in_value,
      'company'             : self.doc.company,
      'fiscal_year'         : self.doc.fiscal_year,
      'is_cancelled'        : (update_stock==1) and 'No' or 'Yes',
      'batch_no'            : d[5],
      'serial_no'           : d[6]
    })


  # SEND SMS
  # ============================================================================================
  def send_sms(self):
    if not self.doc.customer_mobile_no:
      msgprint("Please enter customer mobile no")
    elif not self.doc.message:
      msgprint("Please enter the message you want to send")
    else:
      msgprint(get_obj("SMS Control", "SMS Control").send_sms([self.doc.customer_mobile_no,], self.doc.message))


#------------ check credit limit of items in DN Detail which are not fetched from sales order----------
  def credit_limit(self):
    amount, total = 0, 0
    for d in getlist(self.doclist, 'delivery_note_details'):
      if not d.prevdoc_docname:
        amount += d.amount
    if amount != 0:
      total = (amount/self.doc.net_total)*self.doc.grand_total
      get_obj('Sales Common').check_credit(self, total)

  # on update
  def on_update(self):
    self.set_actual_qty()
    get_obj('Stock Ledger').scrub_serial_nos(self)

  # Repair Delivery Note
  # ===========================================
  def repair_delivery_note(self):
    get_obj('Sales Common', 'Sales Common').repair_curr_doctype_details(self)

  # Packing Slip Related
  # ==========================================
  #def get