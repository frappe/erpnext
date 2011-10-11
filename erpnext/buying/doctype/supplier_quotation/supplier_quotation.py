class DocType:
  def __init__(self,doc,doclist=[]):
    self.doc = doc
    self.doclist = doclist
    self.fname = 'supplier_quotation_details'
    self.tname = 'Supplier Quotation Detail'

  def autoname(self):
    self.doc.name = make_autoname(self.doc.naming_series+'.#####')

  def get_contact_details(self):
    cd = sql("select concat_ws(' ',t2.first_name,t2.last_name),t2.contact_no, t2.email_id, t2.supplier, t2.supplier_name, t2.supplier_address from `tabProfile` t1, `tabContact` t2 where t1.email=t2.email_id and t1.name=%s", session['user'])
    ret = {
      'contact_person'  : cd and cd[0][0] or '',
      'contact_no'      : cd and cd[0][1] or '',
      'email'           : cd and cd[0][2] or '',
      'supplier'   : cd and cd[0][3] or '',
      'supplier_name'   : cd and cd[0][4] or '',
      'supplier_address': cd and cd[0][5] or ''
    }
    return ret

  def get_rfq_details(self):
    self.doc.clear_table(self.doclist, 'supplier_quotation_details')
    get_obj('DocType Mapper','RFQ-Supplier Quotation').dt_map('RFQ','Supplier Quotation',self.doc.rfq_no, self.doc, self.doclist, "[['RFQ Detail', 'Supplier Quotation Detail']]")

  #update approval status
  def update_approval_status(self):
    if not self.doc.approval_status or self.doc.approval_status == 'Not Approved':
      set(self.doc, 'approval_status','Approved')
      return self.doc.approval_status
    elif self.doc.approval_status == 'Approved':
      pc_obj = get_obj('Purchase Common')
      pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Order', docname = self.doc.name, detail_doctype = 'PO Detail')
      set(self.doc, 'approval_status', 'Not Approved')
      return self.doc.approval_status
  
  def validate_item_list(self):
    if not getlist(self.doclist, 'supplier_quotation_details'):
      msgprint("Please fetch RFQ details against which this quotation is prapared")
      raise Exception
  
  # On Validate
  #---------------------------------------------------------------------------------------------------------
  def validate(self):
    self.validate_item_list()
    pc_obj = get_obj(dt='Purchase Common')
    pc_obj.validate_for_items(self)
    pc_obj.validate_conversion_rate(self)
    pc_obj.validate_doc(obj = self, prevdoc_doctype = 'RFQ', prevdoc_docname = self.doc.rfq_no)
  
  def on_update(self):
    set(self.doc, 'status', 'Draft')
  
  # checks whether previous documents doctstatus is submitted.
  def check_previous_docstatus(self):
    pc_obj = get_obj(dt = 'Purchase Common')
    for d in getlist(self.doclist, 'rfq_details'):
      if d.prevdoc_docname:
        pc_obj.check_docstatus(check = 'Previous', doctype = 'Indent', docname = d.prevdoc_docname)
  
  #update rfq
  def update_rfq(self, status):
    prevdoc=''
    for d in getlist(self.doclist, 'supplier_quotation_details'):
      if d.prevdoc_docname:
        prevdoc = d.prevdoc_docname
    
    if status == 'Submitted':
      sql("update `tabRFQ` set status = 'Quotation Received' where name=%s", prevdoc)
    elif status == 'Cancelled':
      sql("update `tabRFQ` set status = 'Submitted' where name=%s", prevdoc)
  
  # On Submit
  def on_submit(self):
    # checks whether previous documents doctstatus is submitted.
    self.check_previous_docstatus() 
    set(self.doc, 'status', 'Submitted')
    self.update_rfq('Submitted')
  
  # On Cancel
  #---------------------------------------------------------------------------------------------------------
  #def check_next_docstatus(self):
  #  submitted = sql("selct name from `tabPurchase Order` where ref_sq = '%s' and docstatus = 1" % self.doc.name)
  #  if submitted:
  #    msgprint("Purchase Order : " + cstr(submitted[0][0]) + " has already been submitted !")
  #    raise Exception
    
  def on_cancel(self):
    pc_obj = get_obj('Purchase Common')
    pc_obj.check_docstatus(check = 'Next', doctype = 'Purchase Order', docname = self.doc.name, detail_doctype = 'PO Detail')
    #self.check_next_docstatus()
    set(self.doc, 'status', 'Cancelled')
    self.update_rfq('Cancelled')

  # GET TERMS & CONDITIONS
  # =====================================================================================
  def get_tc_details(self):
    return get_obj('Purchase Common').get_tc_details(self)

  # Get Supplier Details
  # --------------------
  def get_supplier_details(self, name = ''):
    return get_obj('Purchase Common').get_supplier_details(name)