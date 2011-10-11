import webnotes

from webnotes.model.doc import Document
from webnotes.utils import load_json, cint, cstr
from webnotes import msgprint, errprint

def make_address():
	from webnotes.modules.module_manager import reload_doc
	reload_doc('utilities','doctype','address')
	
	from webnotes.model.db_schema import updatedb
	updatedb('Address')

def make_address_from_customer():
	for c in webnotes.conn.sql("select * from tabCustomer", as_dict=1):		
		d = Document('Address') 
		d.address_line1 = c['address_line1'] 
		d.address_line2 = c['address_line2']  
		d.city = c['city']  
		d.country = c['country']  
		d.pincode = c['pincode']
		d.state = c['state']  
		d.fax = c['fax_1']  
		d.email_id = c['email_id']  		
		d.phone = c['phone_1']  
		d.customer = c['name']  
		d.customer_name = c['customer_name']  
		d.is_primary_address = 1
		d.address_type = 'Office'
		try:
			d.save(1)
		except NameError, e:
			pass

def make_address_from_supplier():
	for c in webnotes.conn.sql("select * from tabSupplier", as_dict=1):		
		d = Document('Address')
		d.address_line1 = c['address_line1'] 
		d.address_line2 = c['address_line2']  
		d.city = c['city']  
		d.country = c['country']  
		d.pincode = c['pincode']
		d.state = c['state']  		  		
		d.supplier = c['name']  
		d.supplier_name = c['supplier_name']  
		d.is_primary_address = 1
		d.address_type = 'Office'
		try:
			d.save(1)
		except NameError, e:
			pass

def make_contact_from_contacttab():
	webnotes.conn.sql("""
	update ignore tabContact set
		is_primary_contact = if(is_primary_contact='Yes',1,0)
	""")

	webnotes.conn.sql("""
	update ignore tabContact t1, tabCustomer t2 set
		t1.name = concat(ifnull(t1.contact_name,t1.name), '-', ifnull(t1.customer_name, t2.name))
		where ifnull(t1.is_customer,0)=1
		and t1.customer = t2.name
	""")

	webnotes.conn.sql("""
	update ignore tabContact t1, tabSupplier t2 set
		t1.name = concat(ifnull(t1.contact_name,t1.name), '-', ifnull(t1.supplier_name, t2.name))
		where ifnull(t1.is_supplier,0)=1
		and t1.supplier = t2.name
	""")

	webnotes.conn.sql("""
	update ignore tabContact set
		name = concat(ifnull(contact_name,name), '-', sales_partner)
		where ifnull(is_sales_partner,0)=1
	""")

	webnotes.conn.commit()
	try:
		webnotes.conn.sql("""alter table tabContact change contact_no phone varchar(180)""")
		webnotes.conn.sql("""alter table tabContact change is_primary_contact is_primary_contact int(1)""")
	except:
		pass
	webnotes.conn.begin()
	
def delete_unwanted_fields():
	delete_fields = [
		('Contact', 'is_sales_partner'), ('Contact', 'sales_partner_address'), ('Contact', 'partner_type'), ('Contact', 'disable_login'), ('Contact', 'contact_address'), ('Contact', 'fax'), ('Contact', 'company_name'), ('Contact', 'contact_no'), ('Contact', 'customer_group'), ('Contact', 'has_login'), ('Contact', 'Create Login'), ('Contact', 'contact_name'), ('Contact', 'company_address'), ('Contact', 'customer_address'), ('Contact', 'supplier_address'), ('Contact', 'supplier_type'), ('Contact', 'is_customer'), ('Contact', 'is_supplier'), ('Contact', 'employee_id'), ('Contact', 'is_employee'), 
		('Customer', 'region'), ('Customer', 'pincode'), ('Customer', 'city'), ('Customer', 'country'), ('Customer', 'state'), ('Customer', 'address'), ('Customer', 'telephone'), ('Customer', 'address_line2'), ('Customer', 'address_line1'), ('Customer', 'last_sales_order'), ('Customer', 'Shipping HTML'), ('Customer', 'phone_1'), ('Customer', 'Territory Help'), ('Customer', 'CG Help'), ('Customer', 'fax_1'), ('Customer', 'email_id'), 
		('Customer Issue', 'email_id'), ('Customer Issue', 'contact_no'),
		('Delivery Note', 'customer_mobile_no'), ('Delivery Note', 'Send SMS'), ('Delivery Note', 'Get Other Charges'), ('Delivery Note', 'message'), ('Delivery Note', 'shipping_address'), ('Delivery Note', 'ship_to'), ('Delivery Note', 'ship_det_no'), ('Delivery Note', 'contact_no'), ('Delivery Note', 'Customer Details'), ('Delivery Note', 'email_id'), ('Delivery Note', 'delivery_address'), ('Delivery Note', 'Contact Help'), ('Delivery Note', 'Territory Help'), 
		('Enquiry', 'address'), ('Enquiry', 'Send Email'), ('Enquiry', 'enquiry_attachment_detail'), ('Enquiry', 'contact_date_ref'), ('Enquiry', 'Update Follow up'), ('Enquiry', 'email_id1'), ('Enquiry', 'cc_to'), ('Enquiry', 'subject'), ('Enquiry', 'message'), ('Enquiry', 'Attachment Html'), ('Enquiry', 'Create New File'), ('Enquiry', 'contact_no'), ('Enquiry', 'email_id'), ('Enquiry', 'project'), ('Enquiry', 'update_follow_up'), ('Enquiry', 'Contact Help'), 
		('Installation Note', 'address'), 
		('Lead', 'message'), ('Lead', 'Send Email'), ('Lead', 'address'), ('Lead', 'subject'), ('Lead', 'contact_no'), ('Lead', 'TerritoryHelp'), 
		('Maintenance Schedule', 'address'), 
		('Maintenance Visit', 'address'), 
		('Purchase Order', 'Contact Help'), ('Purchase Order', 'supplier_qtn'), ('Purchase Order', 'contact_no'), ('Purchase Order', 'email'), 
		('Purchase Receipt', 'Contact Help'), 
		('Quotation', 'email_id'), ('Quotation', 'contact_no'), ('Quotation', 'Update Follow up'), ('Quotation', 'contact_date_ref'), ('Quotation', 'Territory Help'), ('Quotation', 'Contact Help'), 
		('Receivable Voucher', 'Territory Help'), 
		('Sales Order', 'contact_no'), ('Sales Order', 'email_id'), ('Sales Order', 'Contact Help'), ('Sales Order', 'file_list'), ('Sales Order', 'ship_det_no'), ('Sales Order', 'mobile_no'), ('Sales Order', 'Territory Help'), ('Sales Order', 'ship_to'), ('Sales Order', 'Customer Details'), 
		('Sales Partner', 'area_code'), ('Sales Partner', 'telephone'), ('Sales Partner', 'email'), ('Sales Partner', 'address'), ('Sales Partner', 'TerritoryHelp'), ('Sales Partner', 'pincode'), ('Sales Partner', 'country'), ('Sales Partner', 'city'), ('Sales Partner', 'address_line2'), ('Sales Partner', 'address_line1'), ('Sales Partner', 'mobile'), ('Sales Partner', 'state'), 
		('Serial No', 'supplier_address'), 
		('Supplier', 'city'), ('Supplier', 'country'), ('Supplier', 'state'), ('Supplier', 'address_line1'), ('Supplier', 'last_purchase_order'), ('Supplier', 'address'), ('Supplier', 'address_line2'), ('Supplier', 'pincode'), ('Supplier rating', 'address'), ('Supplier rating', 'select'), ('Supplier rating', 'supplier')]
	for d in delete_fields:
		webnotes.conn.sql("delete from tabDocField where parent=%s and if(ifnull(fieldname,'')='',ifnull(label,''),fieldname)=%s", (d[0], d[1]))

#def gen_txt_files():
#	from webnotes.modules.export_module import export_to_files
#	for dt in ['Contact','Customer','Customer Issue','Delivery Note','Enquiry','Installation Note','Lead','Maintenance Schedule','Maintenance Visit','Purchase Order','Purchase Receipt','Quotation','Receivable Voucher','Sales Order','Sales Partner','Serial No','Supplier']:
#		export_to_files(record_list=[['DocType',dt]])

def reload_doc_files():
	from webnotes.modules.module_manager import reload_doc	
	reload_doc('utilities', 'doctype', 'contact')
	reload_doc('selling', 'doctype', 'customer')
	reload_doc('support', 'doctype', 'customer_issue')
	reload_doc('stock', 'doctype', 'delivery_note')
	reload_doc('selling', 'doctype', 'enquiry')
	reload_doc('selling', 'doctype', 'installation_note')
	reload_doc('selling', 'doctype', 'lead')
	reload_doc('support', 'doctype', 'maintenance_schedule')
	reload_doc('support', 'doctype', 'maintenance_visit')
	reload_doc('buying', 'doctype', 'purchase_order')
	reload_doc('stock', 'doctype', 'purchase_receipt')
	reload_doc('selling', 'doctype', 'quotation')
	reload_doc('accounts', 'doctype', 'receivable_voucher')
	reload_doc('accounts', 'doctype', 'payable_voucher')	
	reload_doc('selling', 'doctype', 'sales_order')
	reload_doc('setup', 'doctype', 'sales_partner')
	reload_doc('stock', 'doctype', 'serial_no')
	reload_doc('buying', 'doctype', 'supplier')
	
def reload_mapper_files():
	from webnotes.modules.module_manager import reload_doc	
	reload_doc('Mapper', 'DocType Mapper', 'Customer Issue-Maintenance Visit')
	reload_doc('Mapper', 'DocType Mapper', 'Delivery Note-Installation Note')
	reload_doc('Mapper', 'DocType Mapper', 'Delivery Note-Receivable Voucher')
	reload_doc('Mapper', 'DocType Mapper', 'Enquiry-Quotation')
	reload_doc('Mapper', 'DocType Mapper', 'Lead-Customer')
	reload_doc('Mapper', 'DocType Mapper', 'Lead-Enquiry')
	reload_doc('Mapper', 'DocType Mapper', 'Purchase Order-Payable Voucher')
	reload_doc('Mapper', 'DocType Mapper', 'Purchase Order-Purchase Receipt')
	reload_doc('Mapper', 'DocType Mapper', 'Purchase Receipt-Payable Voucher')
	reload_doc('Mapper', 'DocType Mapper', 'Quotation-Sales Order')
	reload_doc('Mapper', 'DocType Mapper', 'Receivable Voucher-Delivery Note')
	reload_doc('Mapper', 'DocType Mapper', 'Sales Order-Delivery Note')
	reload_doc('Mapper', 'DocType Mapper', 'Sales Order-Maintenance Schedule')
	reload_doc('Mapper', 'DocType Mapper', 'Sales Order-Maintenance Visit')
	reload_doc('Mapper', 'DocType Mapper', 'Sales Order-Receivable Voucher')		
  	
def delete_unwanted_mapper_fields():
	delete_fields = [
	('Customer Issue-Maintenance Visit', 'customer_address', 'address'),
	('Delivery Note-Installation Note', 'customer_address', 'address'),
	('Enquiry-Quotation', 'contact_no', 'contact_no'), ('Enquiry-Quotation', 'subject', 'enq_det'), ('Enquiry-Quotation', 'customer_name', 'customer_name'), ('Enquiry-Quotation', 'customer_name', 'customer_name'), ('Enquiry-Quotation', 'address', 'customer_address'), ('Enquiry-Quotation', 'email_id', 'email_id'),
	('Quotation-Sales Order', 'contact_no', 'contact_no'), ('Quotation-Sales Order', 'email_id', 'email_id'), ('Quotation-Sales Order', 'customer_mobile_no', 'customer_mobile_no'),
	('Sales Order-Delivery Note', 'customer_address', 'delivery_address'), ('Sales Order-Delivery Note', 'customer_address', 'customer_address'), ('Sales Order-Delivery Note', 'contact_no', 'contact_no'), ('Sales Order-Delivery Note', 'email_id', 'email_id'), ('Sales Order-Delivery Note', 'ship_det_no', 'ship_det_no'), ('Sales Order-Delivery Note', 'ship_to', 'ship_to'), ('Sales Order-Delivery Note', 'shipping_address', 'shipping_address'), ('Sales Order-Delivery Note', 'customer_mobile_no', 'customer_mobile_no'),
	('Sales Order-Maintenance Schedule', 'customer_address', 'address'),
	('Sales Order-Maintenance Visit', 'customer_address', 'address'),
	('Sales Order-Receivable Voucher', 'contact_no', 'contact_no')]
	
  	for rec in delete_fields:  		
		webnotes.conn.sql("delete from `tabField Mapper Detail` where parent=%s and from_field=%s and to_field=%s",(rec[0], rec[1], rec[2]))
  	
def sync_docfield_properties():
	update_fields = [	
	('Contact', 'customer', 'Customer', 0L, None, 0L, None), ('Contact', 'supplier', 'Supplier', 0L, None, None, None), ('Contact', 'is_primary_contact', None, 0L, None, None, None), ('Contact', 'email_id', None, 0L, 1L, None, None), ('Contact', 'department', 'Suggest', 0L, None, None, None), ('Contact', 'designation', 'Suggest', 0L, None, None, None),
	('Customer Issue', 'customer', 'Customer', 0L, 1L, 1L, None), ('Customer Issue', 'customer_address', 'Address', 0L, None, 1L, None), ('Customer Issue', 'contact_person', 'Contact', 0L, None, 1L, None), ('Customer Issue', 'customer_name', None, 1L, None, None, None), ('Customer Issue', 'company', 'Company', 0L, 1L, 1L, None), ('Customer Issue', 'fiscal_year', 'link:Fiscal Year', 0L, 1L, 1L, None),
	('Delivery Note', 'customer_address', 'Address', 0L, None, 1L, None), ('Delivery Note', 'contact_person', 'Contact', 0L, None, 1L, None), ('Delivery Note', 'customer_name', None, 1L, None, None, None), ('Delivery Note', 'status', '\nDraft\nSubmitted\nCancelled', 1L, 1L, 1L, None), ('Delivery Note', 'territory', 'Territory', 0L, 1L, 1L, 0L), ('Delivery Note', 'customer_group', 'Customer Group', 0L, None, 1L, None), ('Delivery Note', 'transporter_name', None, 0L, 0L, 1L, None), ('Delivery Note', 'lr_no', None, 0L, 0L, 1L, None), ('Delivery Note', 'lr_date', None, 0L, None, 1L, None), ('Delivery Note', 'currency', 'link:Currency', 0L, 1L, 1L, None), ('Delivery Note', 'letter_head', 'link:Letter Head', 0L, None, 1L, None),
	('Enquiry', 'contact_person', 'Contact', 0L, None, 1L, None), ('Enquiry', 'customer_name', None, 1L, None, 0L, None), ('Enquiry', 'lead', 'Lead', 0L, None, 1L, 0L), ('Enquiry', 'enquiry_type', '\nSales\nMaintenance', 0L, 1L, None, None), ('Enquiry', 'territory', 'Territory', 0L, 1L, 1L, None), ('Enquiry', 'customer_group', 'Customer Group', 0L, 0L, 1L, 0L), ('Enquiry', 'contact_by', 'Profile', 0L, None, None, None),
	('Installation Note', 'contact_person', 'Contact', 0L, None, 1L, None), ('Installation Note', 'customer_name', None, 1L, 0L, None, None), ('Installation Note', 'territory', 'Territory', 0L, 1L, 1L, None), ('Installation Note', 'status', 'Draft\nSubmitted\nCancelled', 1L, 1L, 1L, None),
	('Lead', 'city', None, 0L, 1L, 1L, None), ('Lead', 'country', 'link:Country', 0L, 1L, 1L, None), ('Lead', 'state', 'Suggest', 0L, None, 1L, None), ('Lead', 'company', 'Company', 0L, 1L, None, None), ('Lead', 'contact_by', 'Profile', 0L, 0L, 0L, 0L),
	('Maintenance Schedule', 'customer', 'Customer', 0L, 1L, 1L, None), ('Maintenance Schedule', 'contact_person', 'Contact', 0L, None, 1L, None), ('Maintenance Schedule', 'status', '\nDraft\nSubmitted\nCancelled', 1L, 1L, None, None), ('Maintenance Schedule', 'territory', 'Territory', 0L, 1L, None, None),
	('Maintenance Visit', 'customer', 'Customer', 0L, 1L, 1L, None), ('Maintenance Visit', 'contact_person', 'Contact', 0L, None, 1L, None), ('Maintenance Visit', 'customer_name', None, 1L, None, None, None), ('Maintenance Visit', 'company', 'link:Company', 0L, 1L, 1L, None), ('Maintenance Visit', 'fiscal_year', 'link:Fiscal Year', 0L, 1L, 1L, None), ('Maintenance Visit', 'status', '\nDraft\nCancelled\nSubmitted', 1L, 1L, None, None), ('Maintenance Visit', 'territory', 'Territory', 0L, None, 1L, None),
	('Purchase Order', 'supplier_address', 'Address', 0L, None, 1L, None), ('Purchase Order', 'contact_person', 'Contact', 0L, None, 1L, None), ('Purchase Order', 'supplier_name', None, 1L, None, None, None), ('Purchase Order', 'status', '\nDraft\nSubmitted\nStopped\nCancelled', 1L, 1L, 1L, None), ('Purchase Order', 'indent_no', 'Indent', 0L, None, 1L, 0L), ('Purchase Order', 'is_subcontracted', '\nYes\nNo', 0L, None, 1L, None), ('Purchase Order', 'currency', 'link:Currency', 0L, 1L, 1L, None), ('Purchase Order', 'net_total', None, 1L, 0L, 1L, None),
	('Purchase Receipt', 'supplier_address', 'Address', 0L, None, 1L, None), ('Purchase Receipt', 'contact_person', 'Contact', 0L, None, 1L, None), ('Purchase Receipt', 'supplier_name', None, 1L, None, None, None), ('Purchase Receipt', 'status', '\nDraft\nSubmitted\nCancelled', 1L, 1L, 1L, None), ('Purchase Receipt', 'currency', 'link:Currency', 0L, 1L, 1L, None),
	('Quotation', 'customer', 'Customer', 0L, None, 1L, 0L), ('Quotation', 'customer_address', 'Address', 0L, None, 1L, 0L), ('Quotation', 'contact_person', 'Contact', 0L, 0L, 1L, 0L), ('Quotation', 'customer_name', None, 1L, None, None, None), ('Quotation', 'lead', 'Lead', 0L, None, 1L, 0L), ('Quotation', 'lead_name', None, 1L, None, None, None), ('Quotation', 'order_type', '\nSales\nMaintenance', 0L, 1L, 0L, None), ('Quotation', 'status', '\nDraft\nSubmitted\nOrder Confirmed\nOrder Lost\nCancelled', 1L, 1L, 1L, None), ('Quotation', 'territory', 'Territory', 0L, 1L, 1L, 0L), ('Quotation', 'currency', 'link:Currency', 0L, 1L, 1L, None), ('Quotation', 'letter_head', 'link:Letter Head', 0L, None, 1L, None), ('Quotation', 'order_lost_reason', None, 1L, None, 1L, None), ('Quotation', 'contact_by', 'Profile', 0L, None, 1L, None), ('Quotation', 'contact_date', None, 0L, None, 1L, None), ('Quotation', 'to_discuss', None, 0L, None, 1L, None),
	('Receivable Voucher', 'debit_to', 'Account', 0L, 1L, 1L, None), ('Receivable Voucher', 'customer_address', 'Address', 0L, None, 1L, None), ('Receivable Voucher', 'territory', 'Territory', 0L, 1L, 1L, None), ('Receivable Voucher', 'paid_amount', None, 0L, None, 1L, None), ('Receivable Voucher', 'company', 'Company', 0L, 1L, 1L, None), ('Receivable Voucher', 'fiscal_year', 'link:Fiscal Year', 0L, 1L, 1L, None), ('Receivable Voucher', 'outstanding_amount', None, 1L, None, 1L, None),
	('Payable Voucher', 'supplier_address', 'Address', 0L, None, 1L, None), ('Payable Voucher', 'contact_display', None, 1L, None, None, None), ('Payable Voucher', 'contact_mobile', None, 1L, None, None, None), ('Payable Voucher', 'contact_email', None, 1L, None, 1L, None), ('Payable Voucher', 'currency', 'link:Currency', 0L, 1L, 1L, None), ('Payable Voucher', 'conversion_rate', None, 0L, 1L, 1L, None), ('Payable Voucher', 'company', 'Company', 0L, 1L, 1L, None), ('Payable Voucher', 'fiscal_year', 'link:Fiscal Year', 0L, 1L, 1L, None),
	('Sales Order', 'customer_address', 'Address', 0L, None, 1L, 0L), ('Sales Order', 'contact_person', 'Contact', 0L, None, 1L, None), ('Sales Order', 'customer_name', None, 1L, None, None, None), ('Sales Order', 'status', '\nDraft\nSubmitted\nStopped\nCancelled', 1L, 1L, 1L, None), ('Sales Order', 'quotation_date', None, 1L, 0L, 1L, 1L), ('Sales Order', 'currency', 'link:Currency', 0L, 1L, 1L, None), ('Sales Order', 'letter_head', 'link:Letter Head', 0L, None, 1L, None),
	('Sales Partner', 'territory', 'Territory', 0L, 1L, None, None),
	('Supplier', 'company', 'Company', 0L, 1L, None, None)]
	
	for rec in update_fields:
		webnotes.conn.sql("UPDATE `tabDocField` SET options=%s, permlevel=%s, reqd=%s, print_hide=%s, hidden=%s where parent=%s and fieldname=%s",(rec[2], rec[3], rec[4], rec[5], rec[6], rec[0], rec[1]))
	
def run_patch():
	make_address()
  	make_address_from_customer()
  	make_address_from_supplier()
  	make_contact_from_contacttab()
  	delete_unwanted_fields()
	reload_doc_files()
	reload_mapper_files()
	delete_unwanted_mapper_fields()
	sync_docfield_properties()	

#Old Customer Data Sync Patch for "Quotation, SO, PO, RV, PV, DN, PR, Installation Note, Maintenance Schedule, Customer Issue, Maintenance Visit"
#--------------------------------------------------------------

def run_old_data_sync_patch():
	sync_quotation_customer_data()
	sync_sales_order_customer_data()
	sync_purchase_order_supplier_data()
	sync_receivable_voucher_customer_data()
	sync_payable_voucher_supplier_data()
	sync_delivery_note_customer_data()
	sync_purchase_receipt_supplier_data()
	sync_installation_note_customer_data()
	sync_maintenance_schedule_customer_data()
	sync_customer_issue_customer_data()
	sync_maintenance_visit_customer_data()
	sync_lead_phone()
	
#Quotation
def sync_quotation_customer_data():
	data_rec = webnotes.conn.sql("""
	SELECT tq.name as id,tq.customer, 
	ta.name as customer_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM tabQuotation tq, tabAddress ta
	WHERE tq.customer = ta.customer
	AND tq.quotation_to = 'Customer'	
	AND tq.docstatus !=2
	ORDER BY tq.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))											
		
		webnotes.conn.sql("""
		UPDATE tabQuotation SET
			customer_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['customer_address'],address_display,rec['id']))
		
	data_rec = webnotes.conn.sql("""
	SELECT tq.name as id,tq.customer, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM tabQuotation tq, tabContact tc
	WHERE tq.customer = tc.customer 
	AND tq.quotation_to = 'Customer'	
	AND tq.docstatus !=2
	ORDER BY tq.name
	""", as_dict=1)
	
	for rec in data_rec:			
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE tabQuotation SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))
				
		
#Sales Order		
def sync_sales_order_customer_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	ta.name as customer_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabSales Order` t, tabAddress ta
	WHERE t.customer = ta.customer
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Phone: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabSales Order` SET
			customer_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['customer_address'],address_display,rec['id']))		

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabSales Order` t, tabContact tc
	WHERE t.customer = tc.customer 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:					
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabSales Order` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))		
				
#Purchase Order
def sync_purchase_order_supplier_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.supplier, 
	ta.name as supplier_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabPurchase Order` t, tabAddress ta
	WHERE t.supplier = ta.supplier
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabPurchase Order` SET
			supplier_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['supplier_address'],address_display,rec['id']))				

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.supplier, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabPurchase Order` t, tabContact tc
	WHERE t.supplier = tc.supplier 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:					
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabPurchase Order` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))				
		
#Sales Invoice		
def sync_receivable_voucher_customer_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	ta.name as customer_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabReceivable Voucher` t, tabAddress ta
	WHERE t.customer = ta.customer
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabReceivable Voucher` SET
			customer_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['customer_address'],address_display,rec['id']))		
		
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabReceivable Voucher` t, tabContact tc
	WHERE t.customer = tc.customer 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:					
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabReceivable Voucher` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))				
		
#Purchase Invoice
def sync_payable_voucher_supplier_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.supplier, 
	ta.name as supplier_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabPayable Voucher` t, tabAddress ta
	WHERE t.supplier = ta.supplier
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabPayable Voucher` SET
			supplier_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['supplier_address'],address_display,rec['id']))				

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.supplier, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabPayable Voucher` t, tabContact tc
	WHERE t.supplier = tc.supplier 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:					
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabPayable Voucher` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))				
		
#Delivery Note
def sync_delivery_note_customer_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	ta.name as customer_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabDelivery Note` t, tabAddress ta
	WHERE t.customer = ta.customer
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabDelivery Note` SET
			customer_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['customer_address'],address_display,rec['id']))				

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabDelivery Note` t, tabContact tc
	WHERE t.customer = tc.customer 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabDelivery Note` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))				

#Purchase Receipt
def sync_purchase_receipt_supplier_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.supplier, 
	ta.name as supplier_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabPurchase Receipt` t, tabAddress ta
	WHERE t.supplier = ta.supplier
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabPurchase Receipt` SET
			supplier_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['supplier_address'],address_display,rec['id']))				

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.supplier, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabPurchase Receipt` t, tabContact tc
	WHERE t.supplier = tc.supplier 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:					
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabPurchase Receipt` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))				

#Installation Note
def sync_installation_note_customer_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	ta.name as customer_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabInstallation Note` t, tabAddress ta
	WHERE t.customer = ta.customer
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabInstallation Note` SET
			customer_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['customer_address'],address_display,rec['id']))				

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabInstallation Note` t, tabContact tc
	WHERE t.customer = tc.customer 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabInstallation Note` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))				
		
#Maintenance Schedule
def sync_maintenance_schedule_customer_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	ta.name as customer_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabMaintenance Schedule` t, tabAddress ta
	WHERE t.customer = ta.customer
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabMaintenance Schedule` SET
			customer_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['customer_address'],address_display,rec['id']))	

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabMaintenance Schedule` t, tabContact tc
	WHERE t.customer = tc.customer 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabMaintenance Schedule` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))	
				
#Customer Issue
def sync_customer_issue_customer_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	ta.name as customer_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabCustomer Issue` t, tabAddress ta
	WHERE t.customer = ta.customer
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabCustomer Issue` SET
			customer_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['customer_address'],address_display,rec['id']))

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabCustomer Issue` t, tabContact tc
	WHERE t.customer = tc.customer 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabCustomer Issue` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))
		
#Maintenance Visit
def sync_maintenance_visit_customer_data():
	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	ta.name as customer_address, ta.address_line1, ta.address_line2, ta.city, ta.country, ta.pincode, ta.state, ta.phone
	FROM `tabMaintenance Visit` t, tabAddress ta
	WHERE t.customer = ta.customer
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		address_display = cstr((rec['address_line1'] and rec['address_line1'] or '')) + cstr((rec['address_line2'] and '\n' + rec['address_line2'] or '')) + cstr((rec['city'] and '\n'+rec['city'] or '')) + cstr((rec['pincode'] and ', ' + rec['pincode'] or '')) + cstr((rec['state'] and '\n'+rec['state']+', ' or '')) + cstr((rec['country'] and rec['country'] or '')) + '\n' + cstr((rec['phone'] and 'Tel: '+rec['phone'] or ''))
											
		webnotes.conn.sql("""
		UPDATE `tabMaintenance Visit` SET
			customer_address = %s,
			address_display = %s
			WHERE name = %s
		""",(rec['customer_address'],address_display,rec['id']))	

	data_rec = webnotes.conn.sql("""
	SELECT t.name as id,t.customer, 
	tc.name as contact_person, tc.first_name, tc.last_name, tc.email_id, tc.phone as contact_phone, tc.mobile_no, tc.department, tc.designation
	FROM `tabMaintenance Visit` t, tabContact tc
	WHERE t.customer = tc.customer 
	AND t.docstatus !=2
	ORDER BY t.name
	""", as_dict=1)
	
	for rec in data_rec:			
		contact_display = (rec['first_name'] and rec['first_name'] or '') + (rec['last_name'] and ' ' + rec['last_name'] or '')
											
		webnotes.conn.sql("""
		UPDATE `tabMaintenance Visit` SET
			contact_person = %s,
			contact_mobile = %s,
			contact_email = %s,
			contact_display = %s			
			WHERE name = %s
		""",(rec['contact_person'],rec['mobile_no'],rec['email_id'],contact_display,rec['id']))			

#lead phone data sync
def sync_lead_phone():
	webnotes.conn.sql("""
		update ignore tabLead set
			phone = contact_no
			where contact_no is not null			
		""")
