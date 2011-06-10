# Please edit this list and import only required elements
import webnotes

from webnotes.utils import cstr, date_diff, flt, formatdate, get_defaults, getdate, has_common, now, nowdate, replace_newlines, sendmail, set_default, user_format, validate_email_add
from webnotes.model.doc import Document, make_autoname
from webnotes.model.code import get_obj
from webnotes import msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
  def __init__(self, doc, doclist=[]):
    self.doc = doc
    self.doclist = doclist

# ******************************************************* autoname ***********************************************************
  def autoname(self):
    cust_master_name = get_defaults().get('cust_master_name')
    if cust_master_name == 'Customer Name':
   
      # filter out bad characters in name
      #cust = self.doc.customer_name.replace('&','and').replace('.','').replace("'",'').replace('"','').replace(',','').replace('`','')
      cust = self.doc.customer_name

      supp = sql("select name from `tabSupplier` where name = %s", (cust))
      supp = supp and supp[0][0] or ''
      if supp:
        msgprint("You already have a Supplier with same name")
        raise Exception
      else:
        self.doc.name = cust
        
    else:
      self.doc.name = make_autoname(self.doc.naming_series+'.#####')       


# ******************************************************* triggers ***********************************************************
  # ----------------
  # get company abbr
  # -----------------
  def get_company_abbr(self):
    return get_value('Company', self.doc.company, 'abbr')

  # -----------------------------------------------------------------------------------------------------
  # get parent account(i.e receivables group from company where default account head need to be created)
  # -----------------------------------------------------------------------------------------------------
  def get_receivables_group(self):
    g = sql("select receivables_group from tabCompany where name=%s", self.doc.company)
    g = g and g[0][0] or '' 
    if not g:
      msgprint("Update Company master, assign a default group for Receivables")
      raise Exception
    return g
  
# ******************************************************* validate *********************************************************
  # ----------------
  # validate values
  # ----------------
  def validate_values(self):
    # Master name by naming series -> Series field mandatory
    if get_defaults().get('cust_master_name') == 'Naming Series' and not self.doc.naming_series:
      msgprint("Series is Mandatory.")
      raise Exception

  # ---------
  # validate
  # ---------
  def validate(self):
    self.validate_values()

# ******************************************************* on update *********************************************************
  # ------------------------
  # create customer address
  # ------------------------
  def create_customer_address(self):
    addr_flds = [self.doc.address_line1, self.doc.address_line2, self.doc.city, self.doc.state, self.doc.country, self.doc.pincode]
    address_line = "\n".join(filter(lambda x : (x!='' and x!=None),addr_flds))

    if self.doc.phone_1:
      address_line = address_line + "\n" + "Phone: " + cstr(self.doc.phone_1)
    if self.doc.email_id:
      address_line = address_line + "\n" + "E-mail: " + cstr(self.doc.email_id)
    set(self.doc,'address', address_line)
    
    telephone = "(O): " + cstr(self.doc.phone_1) +"\n"+ cstr(self.doc.phone_2) + "\n" + "(M): " +  "\n" + "(fax): " + cstr(self.doc.fax_1)
    set(self.doc,'telephone',telephone)


  # ------------------------------------
  # create primary contact for customer
  # ------------------------------------
  def create_p_contact(self,nm,phn_no,email_id,mob_no,fax,cont_addr):
    c1 = Document('Contact')
    c1.first_name = nm
    c1.contact_name = nm
    c1.contact_no = phn_no
    c1.email_id = email_id
    c1.mobile_no = mob_no
    c1.fax = fax
    c1.contact_address = cont_addr
    c1.is_primary_contact = 'Yes'
    c1.is_customer =1
    c1.customer = self.doc.name
    c1.customer_name = self.doc.customer_name
    c1.customer_address = self.doc.address
    c1.customer_group = self.doc.customer_group
    c1.save(1)


  # ------------------------
  # create customer contact
  # ------------------------
  def create_customer_contact(self):
    contact = sql("select distinct name from `tabContact` where customer_name=%s", (self.doc.customer_name))
    contact = contact and contact[0][0] or ''
    if not contact:
      # create primary contact for individual customer 
      if self.doc.customer_type == 'Individual':
        self.create_p_contact(self.doc.customer_name,self.doc.phone_1,self.doc.email_id,'',self.doc.fax_1,self.doc.address)
    
      # create primary contact for lead
      elif self.doc.lead_name:
        c_detail = sql("select lead_name, company_name, contact_no, mobile_no, email_id, fax, address from `tabLead` where name =%s", self.doc.lead_name, as_dict=1)
        self.create_p_contact(c_detail and c_detail[0]['lead_name'] or '', c_detail and c_detail[0]['contact_no'] or '', c_detail and c_detail[0]['email_id'] or '', c_detail and c_detail[0]['mobile_no'] or '', c_detail and c_detail[0]['fax'] or '', c_detail and c_detail[0]['address'] or '')


  # -------------------
  # update lead status
  # -------------------
  def update_lead_status(self):
    if self.doc.lead_name:
      sql("update `tabLead` set status='Converted' where name = %s", self.doc.lead_name)


  # -------------------------------------------------------------------------
  # create accont head - in tree under receivables_group of selected company
  # -------------------------------------------------------------------------
  def create_account_head(self):
    if self.doc.company :
      abbr = self.get_company_abbr()  
      if not sql("select name from tabAccount where name=%s", (self.doc.name + " - " + abbr)):
        parent_account = self.get_receivables_group()
        arg = {'account_name':self.doc.name,'parent_account': parent_account, 'group_or_ledger':'Ledger', 'company':self.doc.company,'account_type':'','tax_rate':'0','master_type':'Customer','master_name':self.doc.name,'address':self.doc.address}
        # create
        ac = get_obj('GL Control').add_ac(cstr(arg))
        msgprint("Account Head created for "+ac)
    else :
      msgprint("Please Select Company under which you want to create account head")


  # ----------------------------------------
  # update credit days and limit in account
  # ----------------------------------------
  def update_credit_days_limit(self):
    sql("update tabAccount set credit_days = '%s', credit_limit = '%s' where name = '%s'" % (self.doc.credit_days, self.doc.credit_limit, self.doc.name + " - " + self.get_company_abbr()))


  #create address and contact from lead
  def create_lead_address_contact(self):
    if self.doc.lead_name:
      details = sql("select name, lead_name, address_line1, address_line2, city, country, state, pincode, contact_no, mobile_no, fax, email_id from `tabLead` where name = '%s'" %(self.doc.lead_name), as_dict = 1)      
      d = Document('Address') 
      d.address_line1 = details[0]['address_line1'] 
      d.address_line2 = details[0]['address_line2']  
      d.city = details[0]['city']  
      d.country = details[0]['country']  
      d.pincode = details[0]['pincode']
      d.state = details[0]['state']  
      d.fax = details[0]['fax']  
      d.email_id = details[0]['email_id']  		
      d.phone = details[0]['contact_no']  
      d.customer = self.doc.name
      d.customer_name = self.doc.customer_name
      d.is_primary_address = 1
      d.address_type = 'Office'
      try:
        d.save(1)
      except NameError, e:
        pass
        
      c = Document('Contact') 
      c.first_name = details[0]['lead_name'] 
      c.email_id = details[0]['email_id']
      c.phone = details[0]['contact_no']
      c.phone = details[0]['contact_no']  
      c.customer = self.doc.name
      c.customer_name = self.doc.customer_name
      c.is_primary_contact = 1
      try:
        c.save(1)
      except NameError, e:
        pass  

  # ----------
  # on update
  # ----------
  def on_update(self):
    # create customer addr
    #self.create_customer_address()
    # create customer contact
    #self.create_customer_contact()
    # update lead status
    self.update_lead_status()
    # create account head
    self.create_account_head()
    # update credit days and limit in account
    self.update_credit_days_limit()
    #create address and contact from lead    
    self.create_lead_address_contact()

  
# ******************************************************* on trash *********************************************************
  def on_trash(self):
    if self.doc.lead_name:
      sql("update `tabLead` set status='Interested' where name=%s",self.doc.lead_name)
