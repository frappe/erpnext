# Copyright (c) 2022, Frappe Technologies and contributors
# For license information, please see license.txt

from hashlib import new
from locale import currency
from pydoc import describe
import frappe
from frappe import email
from frappe.model.document import Document

from frappe import _, scrub
from frappe.utils import cint
from frappe.utils.data import now
from six import iteritems

from erpnext.accounts.party import get_partywise_advanced_payment_amount
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport

from frappe.utils import cint, cstr, flt, getdate, nowdate
from datetime import datetime, timedelta
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from frappe import utils
from collections import OrderedDict

from frappe.utils import (
	add_days,
	cint,
	cstr,
	date_diff,
	flt,
	formatdate,
	get_fullname,
	get_link_to_form,
	getdate,
	nowdate,
)

from erpnext.accounts.utils import get_currency_precision

from datetime import datetime # from python std library
from frappe.utils import add_to_date

class FollowUp(Document):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	filters = {}
	party_type = "Customer"

	#  This is for Adding Child table in Dialog Rows by Account Reciviable
	@frappe.whitelist()
	def get_accounts(self, name):
		new_acc = []
		# print(" this is get_accounts self", name if name else 0 )
		a = self.get_data()
		
		if a:	
			for i in a :
				if i.party == name:
					# print(" a thi is aaaaaaaaaaaaaaa", i)
					new_acc.append(i)

		fresh_acc = []
		for i in new_acc:
			i["follow_up"] = frappe.db.get_value('Follow Up Level', {"no_of_days": ['<=',i["age"]]}, 'name')		
		# print("Length of new_acc is ",len(new_acc))
			#  Checking for log avaibality for voucher number
			v_no = frappe.db.get_value("Follow Up Logs", {"voucher_no": i.voucher_no, "level_called": i.follow_up}, ["posting_date"])
			allow_after = frappe.db.get_value("Follow Up Level", i.follow_up , "allow_after")
			if not v_no or allow_after == 1:
				# v_no = frappe.db.get_value("Follow Up Logs", {"voucher_no": n.voucher_no, "level_called": n.follow_up}, ["posting_date"])
				fresh_acc.append(i)
		
		self.data.clear()
		print("this is lengtjh", len(fresh_acc))
		if len(fresh_acc) > 0:
			return fresh_acc
		else:
			frappe.msgprint(" No transcations available for follow-up ")	

	# On Dynamic button click on Dialog Box 
	@frappe.whitelist()
	def on_follow_up_button_click(self, follow_up, trans_items, t_date, customer):
		# print(" this is click, this is follow", follow_up, trans_items, t_date, customer )
		comm_voucher_no = " Voucher Type     Voucher No  	   Due Date   Outstanding Amount \n"
		follow = frappe.get_doc("Follow Up Level", follow_up)
		to_add_to_date = follow.no_of_days
		total_due = 0
		log_name = ""
		details_list = []
		# Creating logs
		for i in trans_items:			
			print(" In sidde follow up button click", i.get("follow_up"),  follow_up)

			outstanding = 0
			invoice_amount = 0

			if i["__checked"] == 1 and i["follow_up"] == follow_up :
			# if i["__checked"] == 1 and i["follow_up"] == follow_up and "due_date" in i.keys():
				print(" In sidde follow up button click", i.get("follow_up", follow_up))
				if "due_date" in i.keys() and i["voucher_no"]:
					if i["voucher_type"] == "Sales Invoice":
						print(" this is sales Invoice ............. SI")
						si_cur = frappe.get_value("Sales Invoice", i["voucher_no"], "currency")
						if si_cur == frappe.defaults.get_global_default('currency'):
							print(" this is currency")
							outstanding = i["outstanding_amount"]
							invoice_amount = i["invoice_amount"],
						else: 
							c_rate = frappe.get_value("Sales Invoice", i["voucher_no"], "conversion_rate")
							outstanding = float("{:.2f}".format(i["outstanding_amount"] / c_rate))
							invoice_amount = float("{:.2f}".format(i["invoice_amount"] / c_rate))
					comm_voucher_no += i["voucher_type"] + "    " + i["voucher_no"] + "    " + i["due_date"] + "    " + str(i["outstanding_amount"]) +" \n "
					detail_dict = {"voucher_type": i["voucher_type"],
									"voucher_no": i["voucher_no"] if i["voucher_no"] else "",
									"due_date": i["due_date"],
									"outstanding_amount" : outstanding,
									"invoice_amount" :  invoice_amount,
									"date": frappe.db.get_value("Sales Invoice", i["voucher_no"],  "posting_date"),
									"age": i["age"],
									"currency": frappe.db.get_value("Sales Invoice", i["voucher_no"],  "currency")}
					details_list.append(detail_dict)
				# else: 				
				# 	comm_voucher_no += i["voucher_type"] + "    " + i["voucher_no"] + "    " + str(utils.today()) + "    " + str(i["outstanding_amount"]) +" \n "
				# 	detail_dict = {"voucher_type": i["voucher_type"],
				# 					"voucher_no": i["voucher_no"] if i["voucher_no"] else "",
				# 					"due_date": str(utils.today()),
				# 					"outstanding_amount" :i["outstanding_amount"]}
				# 	details_list.append(detail_dict)

				total_due += outstanding
				# print(" i[__checked]", i["__checked"], i["voucher_type"] )
				new_log = frappe.new_doc("Follow Up Logs")
				new_log.customer = customer
				new_log.voucher_type = i["voucher_type"]
				new_log.voucher_no = i["voucher_no"]
				new_log.outstanding_amount = outstanding
				new_log.posting_date = t_date
				new_log.due_date = i["due_date"] if "due_date" in i.keys() else utils.today()
				new_log.age = i["age"]
				new_log.level_called = follow_up
				new_log.follow_up_date = add_to_date(utils.now(), days= to_add_to_date, as_string=True, as_datetime=True)
				new_log.save(ignore_permissions=True)
				log_name = new_log.name

				# Adding comment on Customer of Follow Up Performed for this invoice
				if log_name:
					print(" Creating Comment for invoice", )
					comm = frappe.new_doc("Comment")
					comm.subject = "Overdue payment reminder"
					comm.comment_type = "Comment" 
					comm.reference_doctype = "Sales Invoice"
					comm.reference_name = i["voucher_no"]
					comm.comment_by = frappe.session.user
					comm.comment_email = frappe.db.get_value("User",{"name":frappe.session.user}, "email")
					
					comm.content = """<div class="ql-editor read-mode"><p>Follow Up Conducted for this Invoice""".format(comm_voucher_no)
					comm.save(ignore_permissions=True)		


				

		if log_name:

			msg = "<div> Dear <b> {0}</b> <br>".format(frappe.db.get_value('Customer', customer, "customer_name"))
			msg += "<p>Exception made if there was a mistake of ours, it seems that the following amount stays unpaid."
			msg += " Please, take appropriate measures in order to carry out this payment within next couple of days."
			msg += " Would your payment have been carried out after this mail was sent, please ignore this message."
			msg += " Do not hesitate to contact our accounting department.</p><br><br>"
			msg += "Transaction Details <br>"
			msg += "<div><table style = 'border: 1px solid black; widht: 100%; text-align:center '>"
			msg += """<tr> 
						<th style = 'border: 1px solid black; width : 20%' >Invoice No</th>
						<th style = 'border: 1px solid black; width : 15%'>Posting Date</th>
						<th style = 'border: 1px solid black; width : 15%'>Due Date</th>
						<th style = 'border: 1px solid black; width : 10%'>Currency</th>
						<th style = 'border: 1px solid black; width : 15%'>Invoice Amt</th>
						<th style = 'border: 1px solid black; width : 15%'>Outstanding Amt</th>
						<th style = 'border: 1px solid black; width : 10%'>Age</th>
						</tr>
					"""
			for d in details_list: 		
				msg += """<tr> 
							<td style = 'border: 1px solid black; width : 20%'>{0}</th>
							<td style = 'border: 1px solid black; width : 15%'>{1}</th>
							<td style = 'border: 1px solid black; width : 15%'>{2}</th>
							<td style = 'border: 1px solid black; width : 10%'>{3}</th>
							<td style = 'border: 1px solid black; width : 15%'>{4}</th>
							<td style = 'border: 1px solid black; width : 15%'>{5}</th>
							<td style = 'border: 1px solid black; width : 10%'>{6} Days</th>
							</tr>
						""".format(d.get("voucher_no"), d.get("date"), d.get("due_date"), d.get("currency"), d.get("invoice_amount"), d.get("outstanding_amount"), d.get("age"))		

			msg += "</table></div><br> Thank You"

			# email_template = frappe.get_doc("Email Template", follow.email_template)
			primary_c = frappe.db.get_value('Customer', customer, "customer_primary_contact")
			email_id = frappe.db.get_list('Contact Email', {"parent":primary_c }, ['email_id'])
			account_manager = frappe.db.get_value('Customer', customer, "account_manager")
			comm_email = ""
			emails = []
			for e in email_id:
				emails.append(e.get('email_id'))
				comm_email += e.get('email_id') +', '

			if account_manager:
				comm_email += account_manager 
			

			#Creating new dict for args for email Template ,comment and ToDo
			args = {}
			args["customer"] = customer
			args["customer_name"] = frappe.db.get_value('Customer', customer, "customer_name")
			args["outstanding_details"] = details_list
			args["total_due"] = "<b>"+ str(total_due) + "</b>"

			# Sending Email
			if follow.send_email == 1:
				# print(" Send Email")
				# email_template = follow.email_template
				# email_template = frappe.get_doc("Email Template", follow.email_template)
				primary_c = frappe.db.get_value('Customer', customer, "customer_primary_contact")
				email_id = frappe.db.get_list('Contact Email', {"parent":primary_c }, ['email_id'])
				# emails = []
				# for e in email_id:
				# 	emails.append(e.get('email_id'))

				if not email_id:
					frappe.throw("Please set Email Id for Customer {0}".format(customer))
				# message = frappe.render_template(email_template.response, args)

				
				self.notify({
				# for post in messages
				# "message": message,
				"message": msg,
				"message_to": comm_email,
				# for email
				"subject": follow.email_subject,
				
				})

				# message = frappe.render_template(email_template.response, args)
				new_comm = frappe.new_doc("Communication")
				
				new_comm.subject = "Invoice Follow Up"
				new_comm.communication_medium = "Email"
				new_comm.sender = frappe.db.get_value("User",{"name":frappe.session.user}, "email")
				new_comm.recipients = comm_email
				# new_comm.content = message
				new_comm.content = msg
				new_comm.communication_type	= "Communication"
				new_comm.status = "Linked"
				new_comm.sent_or_received = "Sent"      
				new_comm.communication_date	= str(utils.today())
				new_comm.sender_full_name = frappe.session.user_fullname
				new_comm.reference_doctype = "Customer"
				new_comm.reference_name = customer
				new_comm.reference_owner = customer
				new_comm.save(ignore_permissions=True)	


			# Send SMS	
			if follow.send_message == 1:
				# print(" Send Message")
				pass
			
			# Adding ToDo if Manual Action in Follow Up Level
			if follow.manual_action == 1:

				desc = "<div><p> Please {0} Customer  <b>{1}</b><br> ".format(follow.action_type, frappe.db.get_value('Customer', customer, "customer_name"))
				desc += "We have send a follow up as following: {0} <br> ".format(msg)
				desc += "ACTION TODO : {0}</p> </div>".format(follow.action_to_do)
				# print(" Adding ToDo")
				todo = frappe.new_doc('ToDo')
				todo.status = "Open"
				todo.priority = "High"
				todo.date = utils.today()
				todo.owner = follow.responsible
				todo.description = desc
				todo.reference_type = "Customer"
				todo.reference_name = customer
				todo.assigned_by = frappe.session.user
				todo.save(ignore_permissions=True)

			
			
			return True
			# elif "due_date" not in i.keys():
			# 	frappe.throw(" No Due Date for Voucher No- {0}".format(i.get("voucher_no")))

	# To Added Customer commitment
	@frappe.whitelist()
	def on_submit_commitment(self, trans_items, customer):
		# print("Adding Commitment")
		site = frappe.utils.get_url()
		# print("this is site", site)
		
		
		commit_amt = 0		
		for i in trans_items:
			
			commit_name = ""
			commit_link = ""
			remarks = ""
			outstanding = invoice_amount = commited_amount = 0
			comp = frappe.defaults.get_user_default('Company')
			currency = frappe.db.get_value("Sales Invoice", i["voucher_no"] , ["currency"])
			remarks = frappe.db.get_value("Sales Invoice", i["voucher_no"] , ["remarks"])
			primary_c, full_name = frappe.db.get_value('Customer', customer, ["customer_primary_contact", "customer_name"])
			email_id = frappe.db.get_list('Contact Email', {"parent":primary_c }, ['email_id'])
			emails = []

			if currency == frappe.defaults.get_global_default('currency'):
				outstanding = i.get("outstanding_amount")
				invoice_amount = i.get("invoice_amount")
				commited_amount = i.get("commited_amount")
			else:	
				c_rate = frappe.get_value("Sales Invoice", i["voucher_no"], "conversion_rate")
				o = i["outstanding_amount"] / c_rate
				outstanding = float("{:.2f}".format(o))
				invoice_amount = float("{:.2f}".format(i["invoice_amount"] / c_rate))
				commited_amount = float("{:.2f}".format(i.get("commited_amount") / c_rate))
			
			account_manager = frappe.db.get_value('Customer', customer, "account_manager")
			comm_email = ""
			for e in email_id:
				emails.append(e.get('email_id'))
				comm_email += e.get('email_id') +', '
			if account_manager:
				comm_email += account_manager 	
			
			
			print(" this is emails", emails)
			
			if "commited_date" in i.keys() and i.get("commited_amount") > 0 and i["voucher_type"] == "Sales Invoice":

				pre_commit = frappe.db.get_list("Payment Receivable Commitment", {"voucher_type": "Sales Invoice", "voucher_no": i["voucher_no"]}, ['name', 'commitment_status', 'commitment_amount'])
				print("pre Commit", pre_commit, len(pre_commit))	
				for p in pre_commit: 
				# frappe.db.sql("Update `tabPayment Receivable Commitment` set commitment_status = "Cancelled" where  ")
					frappe.db.set_value('Payment Receivable Commitment', p.get('name'), 'commitment_status', 'Cancelled')

				commit_amt += commited_amount
				prc = frappe.new_doc("Payment Receivable Commitment")
				prc.customer = customer
				prc.customer_group = i["customer_group"]
				prc.territory = i["territory"]
				prc.due_date = i["due_date"] if "due_date" in i.keys() else utils.today()
				prc.commitment_date = i["commited_date"]
				prc.commitment_amount = commited_amount
				prc.commitment_to = frappe.session.user
				prc.voucher_type = i["voucher_type"]
				prc.invoice_amount = invoice_amount
				prc.total_outstanding = outstanding
				prc.voucher_no = i["voucher_no"]
				prc.total_due = i["total_due"]
				prc.age = i["age"]
				prc.commitment_status = "Active"
				prc.follow_up_level = i["follow_up"]
				prc.save(ignore_permissions=True)
				
				commit_name = prc.name
				commit_link= site+"/app/payment-receivable-commitment/"+ prc.name
			
				comment_v = "Commitment Given on "+ str(utils.today()) +" for Sales Invoice- "+i["voucher_no"]+"  Invoice Amount- "+ str(invoice_amount)
				# comment_v += "  Outstanding Amount- "+str(i["invoice_amount"])+"  Commitment Amount- "+ str(i["commited_amount"])+"  Commitment Date- "+str(i["commited_date"])
			if 	"commited_date" in i.keys() and i["commited_amount"] > 0 and i["voucher_type"] == "Sales Invoice" and commit_name:
				print(" After Creating Commit")
				# Adding comment on Customer of Follow Up Performed
				comm = frappe.new_doc("Comment")
				comm.subject = "Overdue payment commitment"
				comm.comment_type = "Comment" 
				comm.reference_doctype = "Sales Invoice"
				comm.reference_name = i["voucher_no"]
				comm.comment_by = frappe.session.user
				comm.comment_email = frappe.db.get_value("User",{"name":frappe.session.user}, "email")
				comm.content = """<div class="ql-editor read-mode">
								<p>{0}</p><br> <a href="{1}">Click here to view Commitment information. </a>  </div>	""".format(comment_v, commit_link)
				comm.save(ignore_permissions=True)	
				
				# content = "Dear <b>{2}</b><br><br>Commitment given the following Transcation <br>Commitment given on <b>{0}</b> for Sales Invoice <b>{1}</b><br>".format(str(utils.today()), i["voucher_no"], full_name)
				# content += "Invoice Amount <b>{4} {0}</b> and Outstanding Amount <b>{4} {1}</b> <br>You have given commitment of Amount <b>{4} {2} </b> on <b>{3}</b><br><br>".format(str(i["invoice_amount"]), str(i['outstanding_amount']), str(i["commited_amount"]), str(i["commited_date"]), currency)

				content =	"""
								Dear <b> {0}, </b> <br>
								<p>We are thankful for your business and want to acknowledge that we hold your commitment, 
								dated <b>{1}</b> to pay the <b>{2} {3}</b>against an outstanding of <b>{4} {3}</b> against voucher# <b>{5}</b>.<br>
								Please find the voucher details for your reference:
								<br>
								<b>Voucher Type: {6} <br>
								Voucher Number: {5} <br>
								Remarks: {7} <br>
								Currency: {3} <br>
								Total Amount: {8} <br>
								Outstanding Amount: {4} </b>
								<br> <br>
								Making a payment on time enables us to serve you better and we look forward to provide uninterrupted services to you.</p>
				
							""".format(full_name, str(utils.today()), str(commited_amount), currency, 
							str(outstanding), i["voucher_no"], i["voucher_type"], remarks, str(invoice_amount))

				#Adding comment on Customer
				comm = frappe.new_doc("Comment")
				comm.subject = "Overdue payment commitment"
				comm.comment_type = "Comment" 
				comm.reference_doctype = "Customer"
				comm.reference_name = customer
				comm.comment_by = frappe.session.user
				comm.comment_email = frappe.db.get_value("User",{"name":frappe.session.user}, "email")
				comm.content = """<div class="ql-editor read-mode"><p> Commitment given on the following  Transcation </p>
								<p> {0} </p> <br> <a href="{1}">Click here to view Commitment information. </a>  </div>	""".format(content, commit_link)
				comm.save(ignore_permissions=True)		

				if not email_id:
						frappe.throw("Please set Email Id for Customer {0}".format(customer))


				# Sending email
				content += "Thanks<br> <b> {0} </b> ".format(comp)
				
				self.notify({
					# for post in messages
					"message": " <div class='ql-editor read-mode'><p> {0} </p></div>".format(content),
					"message_to": comm_email,
					# for email
					"subject": "Invoice Commitment",
					})

				print(" this is emial,    ddddddddddd", comm_email)
				# Creating New Communication
				new_comm = frappe.new_doc("Communication")
				
				new_comm.subject = "Invoice Commitment"
				new_comm.communication_medium = "Email"
				new_comm.sender = frappe.db.get_value("User",{"name":frappe.session.user}, "email")
				new_comm.recipients = comm_email
				# new_comm.cc = comm_email
				# new_comm.bcc = com_mail
				new_comm.content = "This is content"
				new_comm.content = str(content)
				new_comm.communication_type	= "Communication"
				new_comm.status = "Linked"
				new_comm.sent_or_received = "Sent"
				new_comm.communication_date	= str(utils.today())
				new_comm.sender_full_name = frappe.session.user_fullname
				new_comm.reference_doctype = "Sales Invoice"
				new_comm.reference_name = i["voucher_no"]
				new_comm.reference_owner = customer
				new_comm.save(ignore_permissions=True)

				# frappe.db.set_value("Communication", new_comm.name, 'recipients', comm_email)
				# new_comm.receipents = comm_email
				# new_comm.save()
						
		if commit_amt > 0 :
			return True


	# To send Email
	def notify(self, args):
		args = frappe._dict(args)
		# args -> message, message_to, subject
		print(" args  111 ", args.message_to)
		recipient = []
		# for e in args.message_to:
		# 	recipient.append(e.get('email_id'))
		# contact = args.message_to

		outgoing = frappe.db.get_value("Email Account", {'enable_outgoing': 1, 'default_outgoing':1}, ['email_id'])
		print(" outgoing", outgoing)

		if not outgoing:
			frappe.throw(" Please add Email account with Eable Outgoing and Default Outgoing")
		
		sender      	    = dict()
		# sender['email']     = frappe.get_doc('User', frappe.session.user).email
		sender['email']     = outgoing 
		sender['full_name'] = get_fullname(sender['email'])

		try:
			frappe.sendmail(
				recipients = args.message_to,
				sender = sender['email'],
				subject = args.subject,
				message = args.message,
			)
			frappe.msgprint(_("Email sent to {0}").format(args.message_to))
		except frappe.OutgoingEmailError:
			pass	

	#  This is for Adding Child table by Account Reciviable Summary
	@frappe.whitelist()
	def get_follow_up(self): 
		currency = frappe.get_cached_value('Company', self.company, "default_currency")

		if self.company:
			self.filters['company'] =  self.company

		if self.report_date:
			self.filters['report_date'] =  self.report_date

		if self.ageing_based_on:
			self.filters['ageing_based_on'] = self.ageing_based_on	

		if self.range1:
			self.filters['range1'] = self.range1

		if self.range2:
			self.filters['range2'] = self.range2

		if self.range3:
			self.filters['range3'] = self.range3

		if self.range4:
			self.filters['range4'] = self.range4

		if self.finance_book:
			self.filters['finance_book'] = self.finance_book
		else: 
			self.filters['finance_book'] = ""

		if self.cost_center:
			self.filters['cost_center'] = self.cost_center
		else : 
			self.filters['cost_center'] = ""	

		if self.customer:
			self.filters['customer'] = self.customer	

		if self.customer_group:
			self.filters['customer_group'] = self.customer_group

		if self.payment_terms_template:
			self.filters['payment_terms_template'] = self.payment_terms_template
		else : 
			self.filters['payment_terms_template'] = ""	

		if self.territory:
			self.filters['territory'] = self.territory
		else: 
			self.filters['territory'] = ""	

		if self.sales_partner:
			self.filters['sales_partner'] = self.sales_partner
		else: 
			self.filters['sales_partner'] = ""

		if self.sales_person:
			self.filters['sales_person'] = self.sales_person
		else :
			self.filters['sales_person'] = ""	

		if self.based_on_payment_terms:
			self.filters['based_on_payment_terms'] = self.based_on_payment_terms
		else:
			self.filters['based_on_payment_terms'] = ""	

		if self.show_future_payments:
			self.filters['show_future_payments'] = self.show_future_payments
		else:		
			self.filters['show_future_payments'] = ""

		entry  = self.get_data1(self.args)
		# print(" this is one ", entry)
		# sorting list according to Outstanding DESC
		sorted_entry = sorted(entry, key=lambda d: d['outstanding'], reverse=True)

		# print(" this is type of", type(sorted_entry), entry)

		new_entry = []
		for e in sorted_entry:
			if e.get("party") :
				print(" this is eeeeeeeeeeeee", e)
				# print(" Inside e",  e.get("party"))
				logs = frappe.db.get_value("Follow Up Logs", { "customer" :e.get("party")}, ["level_called", "submitted_date"])
				
				if not logs or  e.get("total_due")>0 :
					# print("not in logs")
					new_entry.append(e)	

				else:
					
					# print("LOG",logs)
					follow_log = frappe.db.get_value("Follow Up Level", logs[0], ["no_of_days"])
					if follow_log:
						# print("No of days",follow_log)
						if  getdate(logs[1]) + timedelta(days=follow_log) > getdate(now()) :
							# print(" Inside date", getdate(logs[1]) + timedelta(days=follow_log), getdate(now()))
							pass
						else: 
							# print(" Uppar ", getdate(logs[1]) + timedelta(days=follow_log) , getdate(now()) + timedelta(days=follow_log))
							new_entry.append(e)	
		# print("eee", new_entry)	

		for i in new_entry:
			self.append("items",{
							"customer" : i.party,
							"customer_name" : i.party_name,
							"advance_amount" : i.advance,
							"invoiced_amount" : i.invoiced,
							"paid_amount" : i.paid,
							"credit_note" : i.credit_note,
							"outstanding_amount" : i.outstanding,
							"range1" : i.range1,
							"range2" : i.range2,
							"range3" : i.range3,
							"range4" : i.range4,
							"range5" : i.range5,
							"total_amount_due" : i.total_due,
							"territory" : "",
							"currency" : currency,
							"customer_group" : "",
							
							})	
		self.filters.clear()
		return True
		
	#  Accounts receivable summary 
	def get_data1(self, args):
		self.data1 = []
		
		self.party_naming_by = frappe.db.get_value(self.args.get("naming_by")[0], None, self.args.get("naming_by")[1])

		self.receivables = ReceivablePayableReport(self.filters).run(args)[1]

		self.get_party_total(args)

		party_advance_amount = get_partywise_advanced_payment_amount(self.party_type,
			self.report_date, self.show_future_payments, self.company) or {}
		
		for party, party_dict in iteritems(self.party_total):
			if party_dict.outstanding == 0:
				continue

			row = frappe._dict()

			row.party = party
			if self.party_naming_by == "Naming Series":
				row.party_name = frappe.get_cached_value(self.party_type, party, scrub(self.party_type) + "_name")

			row.update(party_dict)

			# Advance against party
			row.advance = party_advance_amount.get(party, 0)

			# In AR/AP, advance shown in paid columns,
			# but in summary report advance shown in separate column
			row.paid -= row.advance

			self.data1.append(row)
		print(" this is data1", 1 if self.data1 else 0 )	
		return self.data1

	def get_party_total(self, args):
		self.party_total = frappe._dict()

		for d in self.receivables:
			self.init_party_total(d)

			# Add all amount columns
			for k in list(self.party_total[d.party]):
				if k not in ["currency", "sales_person"]:

					self.party_total[d.party][k] += d.get(k, 0.0)

			# set territory, customer_group, sales person etc
			# self.set_party_details(d)

	def init_party_total(self, row):
		self.party_total.setdefault(row.party, frappe._dict({
			"invoiced": 0.0,
			"paid": 0.0,
			"credit_note": 0.0,
			"outstanding": 0.0,
			"range1": 0.0,
			"range2": 0.0,
			"range3": 0.0,
			"range4": 0.0,
			"range5": 0.0,
			"total_due": 0.0,
			"sales_person": []
		}))		

	def set_party_details(self, row):
		self.party_total[row.party].currency = row.currency

		for key in ('territory', 'customer_group', 'supplier_group'):
			if row.get(key):
				self.party_total[row.party][key] = row.get(key)

		if row.sales_person:
			self.party_total[row.party].sales_person.append(row.sales_person)
	

	# Accounts Reciviable  
	# def set_defaults(self):
		# if not self.filters["company"]:
		# 	self.filters["company"] = frappe.db.get_single_value('Global Defaults', 'default_company')
		

		# if self.filters.get('group_by_party'):
		# 	self.previous_party=''
		# 	self.total_row_map = {}
		# 	self.skip_total_row = 1

	dr_or_cr = ""	
	party_details = {}
	currency_precision = 0
	company_currency = ""
	age_as_on = 0
	data = []
	invoices = set()


	def get_data(self):
		self.age_as_on = getdate(nowdate()) \
			if getdate(self.report_date) > getdate(nowdate()) \
			else getdate(self.report_date)

		self.company_currency = frappe.get_cached_value('Company',  self.company, "default_currency")
		self.currency_precision = get_currency_precision() or 2
		self.dr_or_cr = "debit" if self.party_type == "Customer" else "credit"
		# self.party_type = self.filters.party_type
		self.party_details = {}
		
		self.skip_total_row = 0

		self.get_gl_entries()
		self.get_sales_invoices_or_customers_based_on_sales_person()
		self.voucher_balance = OrderedDict()
		self.init_voucher_balance() # invoiced, paid, credit_note, outstanding

		# Build delivery note map against all sales invoices
		# self.build_delivery_note_map()

		# Get invoice details like bill_no, due_date etc for all invoices
		self.get_invoice_details()

		# fetch future payments against invoices
		self.get_future_payments()

		# Get return entries
		self.get_return_entries()
		# print(" Self date -----------------", 1 if self.data else 0)
		for gle in self.gl_entries:
			self.update_voucher_balance(gle)

		self.build_data()
		if self.data:
			return self.data

	def init_voucher_balance(self):
		# build all keys, since we want to exclude vouchers beyond the report date
		for gle in self.gl_entries:
			# get the balance object for voucher_type
			key = (gle.voucher_type, gle.voucher_no, gle.party)
			if not key in self.voucher_balance:
				self.voucher_balance[key] = frappe._dict(
					voucher_type = gle.voucher_type,
					voucher_no = gle.voucher_no,
					party = gle.party,
					posting_date = gle.posting_date,
					account_currency = gle.account_currency,
					# remarks = gle.remarks if self.filters.get("show_remarks") else None,
					invoiced = 0.0,
					paid = 0.0,
					credit_note = 0.0,
					outstanding = 0.0,
					invoiced_in_account_currency = 0.0,
					paid_in_account_currency = 0.0,
					credit_note_in_account_currency = 0.0,
					outstanding_in_account_currency = 0.0
				)
			self.get_invoices(gle)

		# 	if self.filters.get('group_by_party'):
		# 		self.init_subtotal_row(gle.party)

		# if self.filters.get('group_by_party'):
		# 	self.init_subtotal_row('Total')

	def get_invoices(self, gle):
		if gle.voucher_type in ('Sales Invoice', 'Purchase Invoice'):
			if self.sales_person:
				if gle.voucher_no in self.sales_person_records.get("Sales Invoice", []) \
					or gle.party in self.sales_person_records.get("Customer", []):
						self.invoices.add(gle.voucher_no)
			else:
				self.invoices.add(gle.voucher_no)

	def init_subtotal_row(self, party):
		if not self.total_row_map.get(party):
			self.total_row_map.setdefault(party, {
				'party': party,
				'bold': 1
			})

			for field in self.get_currency_fields():
				self.total_row_map[party][field] = 0.0

	def get_currency_fields(self):
		return ['invoiced', 'paid', 'credit_note', 'outstanding', 'range1',
			'range2', 'range3', 'range4', 'range5']

	def update_voucher_balance(self, gle):
		# get the row where this balance needs to be updated
		# if its a payment, it will return the linked invoice or will be considered as advance
		row = self.get_voucher_balance(gle)
		if not row: return
		# gle_balance will be the total "debit - credit" for receivable type reports and
		# and vice-versa for payable type reports
		gle_balance = self.get_gle_balance(gle)
		gle_balance_in_account_currency = self.get_gle_balance_in_account_currency(gle)

		if gle_balance > 0:
			if gle.voucher_type in ('Journal Entry', 'Payment Entry') and gle.against_voucher:
				# debit against sales / purchase invoice
				row.paid -= gle_balance
				row.paid_in_account_currency -= gle_balance_in_account_currency
			else:
				# invoice
				row.invoiced += gle_balance
				row.invoiced_in_account_currency += gle_balance_in_account_currency
		else:
			# payment or credit note for receivables
			if self.is_invoice(gle):
				# stand alone debit / credit note
				row.credit_note -= gle_balance
				row.credit_note_in_account_currency -= gle_balance_in_account_currency
			else:
				# advance / unlinked payment or other adjustment
				row.paid -= gle_balance
				row.paid_in_account_currency -= gle_balance_in_account_currency

		if gle.cost_center:
			row.cost_center =  str(gle.cost_center)

	def update_sub_total_row(self, row, party):
		total_row = self.total_row_map.get(party)

		for field in self.get_currency_fields():
			total_row[field] += row.get(field, 0.0)

	def append_subtotal_row(self, party):
		sub_total_row = self.total_row_map.get(party)

		if sub_total_row:
			self.data.append(sub_total_row)
			self.data.append({})
			self.update_sub_total_row(sub_total_row, 'Total')

	def get_voucher_balance(self, gle):
		if self.sales_person:
			against_voucher = gle.against_voucher or gle.voucher_no
			if not (gle.party in self.sales_person_records.get("Customer", []) or \
				against_voucher in self.sales_person_records.get("Sales Invoice", [])):
					return

		voucher_balance = None
		if gle.against_voucher:
			# find invoice
			against_voucher = gle.against_voucher

			# If payment is made against credit note
			# and credit note is made against a Sales Invoice
			# then consider the payment against original sales invoice.
			if gle.against_voucher_type in ('Sales Invoice', 'Purchase Invoice'):
				if gle.against_voucher in self.return_entries:
					return_against = self.return_entries.get(gle.against_voucher)
					if return_against:
						against_voucher = return_against

			voucher_balance = self.voucher_balance.get((gle.against_voucher_type, against_voucher, gle.party))

		if not voucher_balance:
			# no invoice, this is an invoice / stand-alone payment / credit note
			voucher_balance = self.voucher_balance.get((gle.voucher_type, gle.voucher_no, gle.party))

		return voucher_balance

	def build_data(self):
		# set outstanding for all the accumulated balances
		# as we can use this to filter out invoices without outstanding
		for key, row in self.voucher_balance.items():
			row.outstanding = flt(row.invoiced - row.paid - row.credit_note, self.currency_precision)
			row.outstanding_in_account_currency = flt(row.invoiced_in_account_currency - row.paid_in_account_currency - \
				row.credit_note_in_account_currency, self.currency_precision)

			row.invoice_grand_total = row.invoiced

			if (abs(row.outstanding) > 1.0/10 ** self.currency_precision) and \
				(abs(row.outstanding_in_account_currency) > 1.0/10 ** self.currency_precision):
				# non-zero oustanding, we must consider this row

				if self.is_invoice(row) and self.based_on_payment_terms:
					# is an invoice, allocate based on fifo
					# adds a list `payment_terms` which contains new rows for each term
					self.allocate_outstanding_based_on_payment_terms(row)

					if row.payment_terms:
						# make separate rows for each payment term
						for d in row.payment_terms:
							if d.outstanding > 0:
								self.append_row(d)

						# if there is overpayment, add another row
						self.allocate_extra_payments_or_credits(row)
					else:
						self.append_row(row)
				else:
					self.append_row(row)

		# if self.filters.get('group_by_party'):
		# 	self.append_subtotal_row(self.previous_party)
		# 	if self.data:
		# 		self.data.append(self.total_row_map.get('Total'))

	def append_row(self, row):
		self.allocate_future_payments(row)
		self.set_invoice_details(row)
		self.set_party_details(row)
		self.set_ageing(row)

		# if self.filters.get('group_by_party'):
		# 	self.update_sub_total_row(row, row.party)
		# 	if self.previous_party and (self.previous_party != row.party):
		# 		self.append_subtotal_row(self.previous_party)
		# 	self.previous_party = row.party

		self.data.append(row)

	def set_invoice_details(self, row):
		invoice_details = self.invoice_details.get(row.voucher_no, {})
		if row.due_date:
			invoice_details.pop("due_date", None)
		row.update(invoice_details)

		# if row.voucher_type == 'Sales Invoice':
		# 	if self.filters.show_delivery_notes:
		# 		self.set_delivery_notes(row)

		# 	if self.filters.show_sales_person and row.sales_team:
		# 		row.sales_person = ", ".join(row.sales_team)
		# 		del row['sales_team']

	def set_delivery_notes(self, row):
		delivery_notes = self.delivery_notes.get(row.voucher_no, [])
		if delivery_notes:
			row.delivery_notes = ', '.join(delivery_notes)

	# def build_delivery_note_map(self):
	# 	if self.invoices and self.filters.show_delivery_notes:
	# 		self.delivery_notes = frappe._dict()

	# 		# delivery note link inside sales invoice
	# 		si_against_dn = frappe.db.sql("""
	# 			select parent, delivery_note
	# 			from `tabSales Invoice Item`
	# 			where docstatus=1 and parent in (%s)
	# 		""" % (','.join(['%s'] * len(self.invoices))), tuple(self.invoices), as_dict=1)

	# 		for d in si_against_dn:
	# 			if d.delivery_note:
	# 				self.delivery_notes.setdefault(d.parent, set()).add(d.delivery_note)

	# 		dn_against_si = frappe.db.sql("""
	# 			select distinct parent, against_sales_invoice
	# 			from `tabDelivery Note Item`
	# 			where against_sales_invoice in (%s)
	# 		""" % (','.join(['%s'] * len(self.invoices))), tuple(self.invoices) , as_dict=1)

	# 		for d in dn_against_si:
	# 			self.delivery_notes.setdefault(d.against_sales_invoice, set()).add(d.parent)

	def get_invoice_details(self):
		self.invoice_details = frappe._dict()
		if self.party_type == "Customer":
			si_list = frappe.db.sql("""
				select name, due_date, po_no
				from `tabSales Invoice`
				where posting_date <= %s
			""",self.report_date, as_dict=1)
			for d in si_list:
				self.invoice_details.setdefault(d.name, d)

			# Get Sales Team
			# if self.filters.show_sales_person:
			# 	sales_team = frappe.db.sql("""
			# 		select parent, sales_person
			# 		from `tabSales Team`
			# 		where parenttype = 'Sales Invoice'
			# 	""", as_dict=1)
			# 	for d in sales_team:
			# 		self.invoice_details.setdefault(d.parent, {})\
			# 			.setdefault('sales_team', []).append(d.sales_person)

		# if self.party_type == "Supplier":
		# 	for pi in frappe.db.sql("""
		# 		select name, due_date, bill_no, bill_date
		# 		from `tabPurchase Invoice`
		# 		where posting_date <= %s
		# 	""", self.filters.report_date, as_dict=1):
		# 		self.invoice_details.setdefault(pi.name, pi)

		# Invoices booked via Journal Entries
		journal_entries = frappe.db.sql("""
			select name, due_date, bill_no, bill_date
			from `tabJournal Entry`
			where posting_date <= %s
		""", self.report_date, as_dict=1)

		for je in journal_entries:
			if je.bill_no:
				self.invoice_details.setdefault(je.name, je)

	def set_party_details(self, row):
		# customer / supplier name
		party_details = self.get_party_details(row.party) or {}
		row.update(party_details)
		# if self.filters(scrub(self.party_type)):
		# 	row.currency = row.account_currency
		# else:
		row.currency = self.company_currency

	def allocate_outstanding_based_on_payment_terms(self, row):
		self.get_payment_terms(row)
		for term in row.payment_terms:

			# update "paid" and "oustanding" for this term
			if not term.paid:
				self.allocate_closing_to_term(row, term, 'paid')

			# update "credit_note" and "oustanding" for this term
			if term.outstanding:
				self.allocate_closing_to_term(row, term, 'credit_note')

		row.payment_terms = sorted(row.payment_terms, key=lambda x: x['due_date'])

	def get_payment_terms(self, row):
		# build payment_terms for row
		payment_terms_details = frappe.db.sql("""
			select
				si.name, si.party_account_currency, si.currency, si.conversion_rate,
				ps.due_date, ps.payment_term, ps.payment_amount, ps.description, ps.paid_amount, ps.discounted_amount
			from `tab{0}` si, `tabPayment Schedule` ps
			where
				si.name = ps.parent and
				si.name = %s
			order by ps.paid_amount desc, due_date
		""".format(row.voucher_type), row.voucher_no, as_dict = 1)


		original_row = frappe._dict(row)
		row.payment_terms = []

		# If no or single payment terms, no need to split the row
		if len(payment_terms_details) <= 1:
			return

		for d in payment_terms_details:
			term = frappe._dict(original_row)
			self.append_payment_term(row, d, term)

	def append_payment_term(self, row, d, term):
		# changes for filters
		if (self.filters["customer"]  and d.currency == d.party_account_currency):
			invoiced = d.payment_amount
		else:
			invoiced = flt(flt(d.payment_amount) * flt(d.conversion_rate), self.currency_precision)

		row.payment_terms.append(term.update({
			"due_date": d.due_date,
			"invoiced": invoiced,
			"invoice_grand_total": row.invoiced,
			"payment_term": d.description or d.payment_term,
			"paid": d.paid_amount + d.discounted_amount,
			"credit_note": 0.0,
			"outstanding": invoiced - d.paid_amount - d.discounted_amount
		}))

		if d.paid_amount:
			row['paid'] -= d.paid_amount + d.discounted_amount

	def allocate_closing_to_term(self, row, term, key):
		if row[key]:
			if row[key] > term.outstanding:
				term[key] = term.outstanding
				row[key] -= term.outstanding
			else:
				term[key] = row[key]
				row[key] = 0
		term.outstanding -= term[key]

	def allocate_extra_payments_or_credits(self, row):
		# allocate extra payments / credits
		additional_row = None
		for key in ('paid', 'credit_note'):
			if row[key] > 0:
				if not additional_row:
					additional_row = frappe._dict(row)
				additional_row.invoiced = 0.0
				additional_row[key] = row[key]

		if additional_row:
			additional_row.outstanding = additional_row.invoiced - additional_row.paid - additional_row.credit_note
			self.append_row(additional_row)

	def get_future_payments(self):
		if self.show_future_payments:
			self.future_payments = frappe._dict()
			future_payments = list(self.get_future_payments_from_payment_entry())
			future_payments += list(self.get_future_payments_from_journal_entry())
			if future_payments:
				for d in future_payments:
					if d.future_amount and d.invoice_no:
						self.future_payments.setdefault((d.invoice_no, d.party), []).append(d)

	def get_future_payments_from_payment_entry(self):
		return frappe.db.sql("""
			select
				ref.reference_name as invoice_no,
				payment_entry.party,
				payment_entry.party_type,
				payment_entry.posting_date as future_date,
				ref.allocated_amount as future_amount,
				payment_entry.reference_no as future_ref
			from
				`tabPayment Entry` as payment_entry inner join `tabPayment Entry Reference` as ref
			on
				(ref.parent = payment_entry.name)
			where
				payment_entry.docstatus < 2
				and payment_entry.posting_date > %s
				and payment_entry.party_type = %s
			""", (self.filters["report_date"], self.party_type), as_dict=1)

	def get_future_payments_from_journal_entry(self):
		# commented block
		pass
		# if self.filters.get('party'):
		# 	amount_field = ("jea.debit_in_account_currency - jea.credit_in_account_currency"
		# 		if self.party_type == 'Supplier' else "jea.credit_in_account_currency - jea.debit_in_account_currency")
		# else:
		# 	amount_field = ("jea.debit - " if self.party_type == 'Supplier' else "jea.credit")

		# return frappe.db.sql("""
		# 	select
		# 		jea.reference_name as invoice_no,
		# 		jea.party,
		# 		jea.party_type,
		# 		je.posting_date as future_date,
		# 		sum({0}) as future_amount,
		# 		je.cheque_no as future_ref
		# 	from
		# 		`tabJournal Entry` as je inner join `tabJournal Entry Account` as jea
		# 	on
		# 		(jea.parent = je.name)
		# 	where
		# 		je.docstatus < 2
		# 		and je.posting_date > %s
		# 		and jea.party_type = %s
		# 		and jea.reference_name is not null and jea.reference_name != ''
		# 	group by je.name, jea.reference_name
		# 	having future_amount > 0
		# 	""".format(amount_field), (self.filters.report_date, self.party_type), as_dict=1)

	def allocate_future_payments(self, row):
		# future payments are captured in additional columns
		# this method allocates pending future payments against a voucher to
		# the current row (which could be greport_dateenerated from payment terms)
		if not self.show_future_payments:
			return

		row.remaining_balance = row.outstanding
		row.future_amount = 0.0
		for future in self.future_payments.get((row.voucher_no, row.party), []):
			if row.remaining_balance > 0 and future.future_amount:
				if future.future_amount > row.outstanding:
					row.future_amount = row.outstanding
					future.future_amount = future.future_amount - row.outstanding
					row.remaining_balance = 0
				else:
					row.future_amount += future.future_amount
					future.future_amount = 0
					row.remaining_balance = row.outstanding - row.future_amount

				row.setdefault('future_ref', []).append(cstr(future.future_ref) + '/' + cstr(future.future_date))

		if row.future_ref:
			row.future_ref = ', '.join(row.future_ref)

	def get_return_entries(self):
		doctype = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"
		filters={
			'is_return': 1,
			'docstatus': 1
		}
		# party_field = scrub(self.filters.party_type)
		# if self.filters.get(party_field):
		# 	filters.update({party_field: self.filters.get(party_field)})
		self.return_entries = frappe._dict(
			frappe.get_all(doctype, filters, ['name', 'return_against'], as_list=1)
		)

	def set_ageing(self, row):
		if self.ageing_based_on == "Due Date":
			# use posting date as a fallback for advances posted via journal and payment entry
			# when ageing viewed by due date
			entry_date = row.due_date or row.posting_date
		elif self.ageing_based_on == "Supplier Invoice Date":
			entry_date = row.bill_date
		else:
			entry_date = row.posting_date

		self.get_ageing_data(entry_date, row)

		# ageing buckets should not have amounts if due date is not reached
		if getdate(entry_date) > getdate(self.report_date):
			row.range1 = row.range2 = row.range3 = row.range4 = row.range5 = 0.0

		row.total_due = row.range1 + row.range2 + row.range3 + row.range4 + row.range5


	def get_ageing_data(self, entry_date, row):
		# [0-30, 30-60, 60-90, 90-120, 120-above]
		row.range1 = row.range2 = row.range3 = row.range4 = row.range5 = 0.0

		if not (self.age_as_on and entry_date):
			return

		row.age = (getdate(self.age_as_on) - getdate(entry_date)).days or 0
		index = None

		if not (self.range1 and self.range2 and self.range3 and self.range4):
			self.range1, self.range2, self.range3, self.range4 = 30, 60, 90, 120

		for i, days in enumerate([self.range1, self.range2, self.range3, self.range4]):
			if cint(row.age) <= cint(days):
				index = i
				break

		if index is None: index = 4
		row['range' + str(index+1)] = row.outstanding

	def get_gl_entries(self):
		# get all the GL entries filtered by the given filters

		conditions, values = self.prepare_conditions()
		order_by = self.get_order_by_condition()

		if self.show_future_payments:
			values.insert(2, self.filters['report_date'])

			date_condition = """AND (posting_date <= %s
				OR (against_voucher IS NULL AND DATE(creation) <= %s))"""
		else:
			date_condition = "AND posting_date <=%s"

		if self.filters.get(scrub(self.party_type)):
			select_fields = "debit_in_account_currency as debit, credit_in_account_currency as credit"
		else:
			select_fields = "debit, credit"

		doc_currency_fields = "debit_in_account_currency, credit_in_account_currency"

		# remarks = ", remarks" if self.filters.get("show_remarks") else ""
		remarks = ""

		self.gl_entries = frappe.db.sql("""
			select
				name, posting_date, account, party_type, party, voucher_type, voucher_no, cost_center,
				against_voucher_type, against_voucher, account_currency, {0}, {1} {remarks}
			from
				`tabGL Entry`
			where
				docstatus < 2
				and is_cancelled = 0
				and party_type=%s
				and (party is not null and party != '')
				{2} {3} {4}"""
			.format(select_fields, doc_currency_fields, date_condition, conditions, order_by, remarks=remarks), values, as_dict=True)

	def get_sales_invoices_or_customers_based_on_sales_person(self):
		if self.sales_person:
			lft, rgt = frappe.db.get_value("Sales Person",
				self.sales_person, ["lft", "rgt"])

			records = frappe.db.sql("""
				select distinct parent, parenttype
				from `tabSales Team` steam
				where parenttype in ('Customer', 'Sales Invoice')
					and exists(select name from `tabSales Person` where lft >= %s and rgt <= %s and name = steam.sales_person)
			""", (lft, rgt), as_dict=1)

			self.sales_person_records = frappe._dict()
			for d in records:
				self.sales_person_records.setdefault(d.parenttype, set()).add(d.parent)

	def prepare_conditions(self):
		conditions = [""]
		values = [self.party_type, self.report_date]
		party_type_field = scrub(self.party_type)

		self.add_common_filters(conditions, values, party_type_field)

		if party_type_field=="customer":
			self.add_customer_filters(conditions, values)

		elif party_type_field=="supplier":
			self.add_supplier_filters(conditions, values)

		if self.cost_center:
			self.get_cost_center_conditions(conditions)

		# self.add_accounting_dimensions_filters(conditions, values)
		return " and ".join(conditions), values

	def get_cost_center_conditions(self, conditions):
		lft, rgt = frappe.db.get_value("Cost Center", self.filters['cost_center'], ["lft", "rgt"])
		cost_center_list = [center.name for center in frappe.get_list("Cost Center", filters = {'lft': (">=", lft), 'rgt': ("<=", rgt)})]

		cost_center_string = '", "'.join(cost_center_list)
		conditions.append('cost_center in ("{0}")'.format(cost_center_string))

	def get_order_by_condition(self):
		# if self.filters.get('group_by_party'):
		# 	return "order by party, posting_date"
		# else:
			return "order by posting_date, party"

	def add_common_filters(self, conditions, values, party_type_field):
		if self.company:
			conditions.append("company=%s")
			values.append(self.company)

		if self.finance_book:
			conditions.append("ifnull(finance_book, '') in (%s, '')")
			values.append(self.finance_book)

		# if self.filters.get(party_type_field):
		# 	conditions.append("party=%s")
		# 	values.append(self.filters.get(party_type_field))

		# get GL with "receivable" or "payable" account_type
		account_type = "Receivable" if self.party_type == "Customer" else "Payable"
		accounts = [d.name for d in frappe.get_all("Account",
			filters={"account_type": account_type, "company": self.company})]

		if accounts:
			conditions.append("account in (%s)" % ','.join(['%s'] *len(accounts)))
			values += accounts

	def add_customer_filters(self, conditions, values):
		# if self.filters["customer_group"]:
		# 	conditions.append(self.get_hierarchical_filters('Customer Group', 'customer_group'))

		# if self.filters["territory"]:
		# 	conditions.append(self.get_hierarchical_filters('Territory', 'territory'))

		if self.payment_terms_template:
			conditions.append("party in (select name from tabCustomer where payment_terms=%s)")
			values.append(self.payment_terms_template)

		if self.sales_partner:
			conditions.append("party in (select name from tabCustomer where default_sales_partner=%s)")
			values.append(self.sales_partner)

	def add_supplier_filters(self, conditions, values):
		# if self.filters.get("supplier_group"):
		# 	conditions.append("""party in (select name from tabSupplier
		# 		where supplier_group=%s)""")
		# 	values.append(self.filters.get("supplier_group"))

		if self.payment_terms_template:
			conditions.append("party in (select name from tabSupplier where payment_terms=%s)")
			values.append(self.payment_terms_template)

	# def get_hierarchical_filters(self, doctype, key):
	# 	lft, rgt = frappe.db.get_value(doctype, self.filters.get(key), ["lft", "rgt"])

	# 	return """party in (select name from tabCustomer
	# 		where exists(select name from `tab{doctype}` where lft >= {lft} and rgt <= {rgt}
	# 			and name=tabCustomer.{key}))""".format(
	# 				doctype=doctype, lft=lft, rgt=rgt, key=key)

	# def add_accounting_dimensions_filters(self, conditions, values):
	# 	accounting_dimensions = get_accounting_dimensions(as_list=False)

	# 	if accounting_dimensions:
	# 		for dimension in accounting_dimensions:
	# 			if self.filters.get(dimension.fieldname):
	# 				if frappe.get_cached_value('DocType', dimension.document_type, 'is_tree'):
	# 					self.filters[dimension.fieldname] = get_dimension_with_children(dimension.document_type,
	# 						self.filters.get(dimension.fieldname))
	# 				conditions.append("{0} in %s".format(dimension.fieldname))
	# 				values.append(tuple(self.filters.get(dimension.fieldname)))

	def get_gle_balance(self, gle):
		# get the balance of the GL (debit - credit) or reverse balance based on report type
		return gle.get(self.dr_or_cr) - self.get_reverse_balance(gle)

	def get_gle_balance_in_account_currency(self, gle):
		# get the balance of the GL (debit - credit) or reverse balance based on report type
		return gle.get(self.dr_or_cr + '_in_account_currency') - self.get_reverse_balance_in_account_currency(gle)

	def get_reverse_balance_in_account_currency(self, gle):
		return gle.get('debit_in_account_currency' if self.dr_or_cr=='credit' else 'credit_in_account_currency')

	def get_reverse_balance(self, gle):
		# get "credit" balance if report type is "debit" and vice versa
		return gle.get('debit' if self.dr_or_cr=='credit' else 'credit')

	def is_invoice(self, gle):
		if gle.voucher_type in ('Sales Invoice', 'Purchase Invoice'):
			return True

	def get_party_details(self, party):
		if not party in self.party_details:
			if self.party_type == 'Customer':
				self.party_details[party] = frappe.db.get_value('Customer', party, ['customer_name',
					'territory', 'customer_group', 'customer_primary_contact'], as_dict=True)
			else:
				self.party_details[party] = frappe.db.get_value('Supplier', party, ['supplier_name',
					'supplier_group'], as_dict=True)

		return self.party_details[party]
