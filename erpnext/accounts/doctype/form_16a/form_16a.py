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
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl
	
	def autoname(self):
		self.doc.name = make_autoname('Form 16A' + '/.#####') 

	# Get pan no and tan no from company
	#-------------------------------------
	def get_registration_details(self):
		comp_det=sql("Select address,registration_details from `tabCompany` where name = '%s'"%(self.doc.company))
		if not comp_det:
			msgprint("Registration Details is not mentioned in comapny")
			ret = {
			'company_address':'',
			'registration_details':	''
		}
		else:
			ret = {
				'company_address': cstr(comp_det[0][0]),
				'registration_details': cstr(comp_det[0][1])
			}	 
		return ret
    
	# Get party details
	#------------------
	def get_party_det(self):		
		party_det=sql("select master_type, master_name from `tabAccount` where name='%s'" % self.doc.party_name)
		if party_det and party_det[0][0]=='Supplier':			
			try:
				rec = sql("select name, address_line1, address_line2, city, country, pincode, state from `tabAddress` where supplier = '%s' and docstatus != 2 order by is_primary_address desc limit 1" %(party_det[0][1]), as_dict = 1)
				address_display = cstr((rec[0]['address_line1'] and rec[0]['address_line1'] or '')) + cstr((rec[0]['address_line2'] and '\n' + rec[0]['address_line2'] or '')) + cstr((rec[0]['city'] and '\n'+rec[0]['city'] or '')) + cstr((rec[0]['pincode'] and '\n' + rec[0]['pincode'] or '')) + cstr((rec[0]['state'] and '\n'+rec[0]['state'] or '')) + cstr((rec[0]['country'] and '\n'+rec[0]['country'] or ''))
			except:
				address_display = ''
				
		ret = {
			'party_address': cstr(address_display)
		}
          	
		return ret
	
	# Get TDS Return acknowledgement
	#-------------------------------
	def get_return_ack_details(self):
		self.doc.clear_table(self.doclist, 'form_16A_ack_details')
		if not (self.doc.from_date and self.doc.to_date):
			msgprint("Please enter From Date, To Date")
		else:
			ack = sql("select quarter, acknowledgement_no from `tabTDS Return Acknowledgement` where date_of_receipt>='%s' and date_of_receipt<='%s' and tds_category = '%s' order by date_of_receipt ASC" % (self.doc.from_date, self.doc.to_date, self.doc.tds_category))
			for d in ack:
				ch = addchild(self.doc, 'form_16A_ack_details', 'Form 16A Ack Detail', 1, self.doclist)
				ch.quarter = d[0]
				ch.ack_no = d[1]

	# Get tds payment details
	#-------------------------------
	def get_tds(self):
		self.doc.clear_table(self.doclist,'form_16A_tax_details')
		import datetime
		if self.doc.from_date and self.doc.to_date and self.doc.tds_category:			
			tot=0.0
			party_tds_list=sql("select t2.amount_paid,t2.date_of_payment,t2.tds_amount,t2.cess_on_tds, t2.total_tax_amount, t1.cheque_no, t1.bsr_code, t1.date_of_receipt, t1.challan_id from `tabTDS Payment` t1, `tabTDS Payment Detail` t2 where t1.tds_category='%s' and t2.party_name='%s' and t1.from_date >= '%s' and t1.to_date <= '%s' and t2.total_tax_amount>0 and t2.parent=t1.name and t1.docstatus=1" % (self.doc.tds_category,self.doc.party_name,self.doc.from_date,self.doc.to_date))
			for s in party_tds_list:
				child = addchild(self.doc, 'form_16A_tax_details', 'Form 16A Tax Detail', 1, self.doclist)
				child.amount_paid = s and flt(s[0]) or ''
				child.date_of_payment =s and s[1].strftime('%Y-%m-%d') or ''
				child.tds_main = s and flt(s[2]) or ''
				child.surcharge = 0
				child.cess_on_tds = s and flt(s[3]) or ''
				child.total_tax_deposited = s and flt(s[4]) or ''
				child.cheque_no = s and s[5] or ''
				child.bsr_code = s and s[6] or ''
				child.tax_deposited_date = s and s[7].strftime('%Y-%m-%d') or ''
				child.challan_no = s and s[8] or ''
				tot=flt(tot)+flt(s[4])
			self.doc.total_amount = flt(tot)
		else:
			msgprint("Plaese enter from date, to date and TDS category")
		
	
	# validate
	#----------------
	def validate(self):
		tot=0.0
		for d in getlist(self.doclist,'form_16A_tax_details'):
			tot=flt(tot)+flt(d.total_tax_deposited)
		
		dcc = TransactionBase().get_company_currency(self.doc.company)
		self.doc.total_amount = flt(tot)		
		self.doc.in_words = get_obj('Sales Common').get_total_in_words(dcc, self.doc.total_amount)
