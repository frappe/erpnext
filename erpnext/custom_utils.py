from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe import msgprint
from frappe.utils import flt, cint, nowdate, getdate, formatdate
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils.data import get_first_day, get_last_day, add_years
from frappe.desk.form.linked_with import get_linked_doctypes, get_linked_docs
from frappe.model.naming import getseries

#function to get the difference between two dates
@frappe.whitelist()
def get_date_diff(start_date, end_date):
	if start_date is None:
		return 0
	elif end_date is None:
		return 0
	else:
		return frappe.utils.data.date_diff(end_date, start_date) + 1

##
# Check for future dates in transactions
##
def check_future_date(date):
	if not date:
		frappe.throw("Date Argument Missing")
	if getdate(date) > getdate(nowdate()):
		frappe.throw("Posting for Future Date is not Permitted")

##
# Get cost center from branch
##
def get_branch_cc(branch):
	if not branch:
		frappe.throw("No Branch Argument Found")
	doc = frappe.get_doc("Branch", branch)
	return doc.cost_center

##
# Rounds to the nearest 5 with precision of 1 by default
##
def round5(x, prec=1, base=0.5):
	return round(base * round(flt(x)/base), prec)

##
# If the document is linked and the linked docstatus is 0 and 1, return the first linked document
##
def check_uncancelled_linked_doc(doctype, docname):
	linked_doctypes = get_linked_doctypes(doctype)
	linked_docs = get_linked_docs(doctype, docname, linked_doctypes)
	for docs in linked_docs:
		for doc in linked_docs[docs]:
			if doc['docstatus'] < 2:
				frappe.throw("There is an uncancelled " + str(frappe.get_desk_link(docs, doc['name']))+ " linked with this document")

def get_year_start_date(date):
	return str(date)[0:4] + "-01-01"

def get_year_end_date(date):
	return str(date)[0:4] + "-12-31"

# Ver 2.0 Begins, following method added by SHIV on 28/11/2017
@frappe.whitelist()
def get_user_info(user=None, employee=None, cost_center=None):
	info = {}
	
	#cost_center,branch = frappe.db.get_value("Employee", {"user_id": user}, ["cost_center", "branch"])

	if employee:
		# Nornal Employee
		cost_center = frappe.db.get_value("Employee", {"name": employee}, "cost_center")
		branch      = frappe.db.get_value("Employee", {"name": employee}, "branch")

		# DES Employee
		if not cost_center:
			cost_center = frappe.db.get_value("DES Employee", {"name": employee}, "cost_center")
			branch      = frappe.db.get_value("DES Employee", {"name": employee}, "branch")

		# MR Employee
		if not cost_center:
			cost_center = frappe.db.get_value("Muster Roll Employee", {"name": employee}, "cost_center")
			branch      = frappe.db.get_value("Muster Roll Employee", {"name": employee}, "branch")
		
	elif user:
		# Normal Employee
		cost_center = frappe.db.get_value("Employee", {"user_id": user}, "cost_center")
		branch      = frappe.db.get_value("Employee", {"user_id": user}, "branch")

		# DES Employee
		if not cost_center:
			cost_center = frappe.db.get_value("DES Employee", {"user_id": user}, "cost_center")
			branch      = frappe.db.get_value("DES Employee", {"user_id": user}, "branch")

		# MR Employee
		if not cost_center:
			cost_center = frappe.db.get_value("Muster Roll Employee", {"user_id": user}, "cost_center")
			branch      = frappe.db.get_value("Muster Roll Employee", {"user_id": user}, "branch")
		
	warehouse   = frappe.db.get_value("Cost Center", cost_center, "warehouse")
	approver    = frappe.db.get_value("Approver Item", {"cost_center": cost_center}, "approver")
	customer    = frappe.db.get_value("Customer", {"cost_center": cost_center}, "name")

	info.setdefault('cost_center', cost_center)
	info.setdefault('branch', branch)
	info.setdefault('warehouse', warehouse)
	info.setdefault('approver',approver)
	info.setdefault('customer', customer)
	
	#return [cc, wh, app, cust]
	return info
# Ver 2.0 Ends

##
#  nvl() function added by SHIV on 02/02/2018
##
def nvl(val1, val2):
	return val1 if val1 else val2

##
# generate and get the receipt number
##
def generate_receipt_no(doctype, docname, branch, fiscal_year):
	if doctype and docname:
		abbr = frappe.db.get_value("Branch", branch, "abbr")
		if not abbr:
			frappe.throw("Set Branch Abbreviation in Branch Master Record")
		name = str("NRDCL/" + str(abbr) + "/" + str(fiscal_year) + "/")
		current = getseries(name, 4)
		doc = frappe.get_doc(doctype, docname)
		doc.db_set("money_receipt_no", current)
		doc.db_set("money_receipt_prefix", name)

##
#  get_prev_doc() function added by SHIV on 03/22/2018
##
@frappe.whitelist()
def get_prev_doc(doctype,docname,col_list=""):
	if col_list:
		return frappe.db.get_value(doctype,docname,col_list.split(","),as_dict=1)
	else:
		return frappe.get_doc(doctype,docname)

##
# Prepre the basic stock ledger 
##
def prepare_sl(d, args):
	sl_dict = frappe._dict({
		"item_code": d.pol_type,
		"warehouse": d.warehouse,
		"posting_date": d.posting_date,
		"posting_time": d.posting_time,
		'fiscal_year': get_fiscal_year(d.posting_date, company=d.company)[0],
		"voucher_type": d.doctype,
		"voucher_no": d.name,
		"voucher_detail_no": d.name,
		"actual_qty": 0,
		"stock_uom": d.stock_uom,
		"incoming_rate": 0,
		"company": d.company,
		"batch_no": "",
		"serial_no": "",
		"project": "",
		"is_cancelled": d.docstatus==2 and "Yes" or "No"
	})

	sl_dict.update(args)
	return sl_dict

##
# Prepre the basic accounting ledger 
##
def prepare_gl(d, args):
	"""this method populates the common properties of a gl entry record"""
	gl_dict = frappe._dict({
		'company': d.company,
		'posting_date': d.posting_date,
		'fiscal_year': get_fiscal_year(d.posting_date, company=d.company)[0],
		'voucher_type': d.doctype,
		'voucher_no': d.name,
		'remarks': d.remarks,
		'debit': 0,
		'credit': 0,
		'debit_in_account_currency': 0,
		'credit_in_account_currency': 0,
		'is_opening': "No",
		'party_type': None,
		'party': None,
		'project': ""
	})
	gl_dict.update(args)

	return gl_dict

def cancel_budget_entry(reference_type, reference_no):
	if frappe.db.exists("Consumed Budget", {"reference_type":str(reference_type), "reference_no":str(reference_no)}):
		doc = frappe.get_doc("Consumed Budget", {"reference_type":str(reference_type), "reference_no":str(reference_no)})
		doc.cancel()
		frappe.db.sql("delete from `tabConsumed Budget` where reference_type = %s and reference_no = %s",(str(reference_type), str(reference_no)))
	if frappe.db.exists("Commited Budget", {"reference_type":str(reference_type), "reference_no":str(reference_no)}):
		doc = frappe.get_doc("Commited Budget", {"reference_type":str(reference_type), "reference_no":str(reference_no)})
		doc.cancel()
		frappe.db.sql("delete from `tabCommitted Budget` where reference_type = %s and reference_no = %s",(str(reference_type), str(reference_no)))
	return

def check_budget_available_for_reappropiation(cost_center, budget_account, transaction_date, amount):
	budget_against = frappe.db.get_single_value("Accounts Settings", "budget_level")
	if not budget_against:
		frappe.throw("Budget Level not set in Accounts Settings")
	cond = ""
	if budget_against == "Cost Center":
		cond += " and b.budget_against = '{}' and b.cost_center = '{}'".format(budget_against, cost_center)
	else:
		cond += " and b.budget_against = '{}'".format(budget_against)
	budget_amount = frappe.db.sql("select b.action_if_annual_budget_exceeded as action, \
					ba.budget_check, ba.budget_amount, b.deviation \
					from `tabBudget` b, `tabBudget Account` ba \
					where b.docstatus = 1 \
					and ba.parent = b.name and ba.account= '{}' \
					and b.fiscal_year = '{}' {} ".format(budget_account, str(transaction_date)[0:4], cond), as_dict=True)
 
	if budget_amount:
		if budget_against == "Cost Center":
			committed = frappe.db.sql("select SUM(cb.amount) as total from `tabCommitted Budget` cb where cb.account=%s and cb.cost_center=%s and cb.po_date between %s and %s", (budget_account, cost_center, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
			consumed = frappe.db.sql("select SUM(cb.amount) as total from `tabConsumed Budget` cb where cb.account=%s and cb.cost_center=%s and cb.po_date between %s and %s", (budget_account, cost_center, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
		else:
			committed = frappe.db.sql("select SUM(cb.amount) as total from `tabCommitted Budget` cb where cb.account=%s and cb.po_date between %s and %s", (budget_account, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
			consumed = frappe.db.sql("select SUM(cb.amount) as total from `tabConsumed Budget` cb where cb.account=%s and cb.po_date between %s and %s", (budget_account, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
		if consumed and committed:
			if flt(consumed[0].total) > flt(committed[0].total):
				committed = consumed
			total_consumed_amount = flt(committed[0].total) + flt(amount)
			if flt(total_consumed_amount) > flt(budget_amount[0].budget_amount):
				frappe.msgprint("Total Amount consumed: {} and Budget Amount:  {}".format(total_consumed_amount, budget_amount[0].budget_amount))
				frappe.throw("Not enough budget in <b>" + str(budget_account) + "</b>. The budget is exceeded by <b>" + str(flt(total_consumed_amount) - flt(budget_amount[0].budget_amount)) + "</b>")
	else:
		frappe.throw("There is no budget allocated in <b>" + str(budget_account) + "</b>")

##
# Check budget availability in the budget head
##
def check_budget_available(cost_center, budget_account, transaction_date, amount, project = None):
	consumed=committed= None
	if project:
		budget_amount = frappe.db.sql("select b.action_if_annual_budget_exceeded as action, \
						ba.budget_check, ba.budget_amount, b.deviation \
						from `tabBudget` b, `tabBudget Cost Center` ba \
						where b.docstatus = 1 \
						and ba.parent = b.name and ba.cost_center= '{}' \
						and b.fiscal_year = '{}' \
						and b.project = '{}' ".format(cost_center, str(transaction_date)[0:4], project), as_dict=True)
		if budget_amount:
			committed = frappe.db.sql("select SUM(cb.amount) as total from `tabCommitted Budget` cb where cb.cost_center=%s and cb.project=%s and cb.reference_date between %s and %s", (cost_center, project, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
			consumed = frappe.db.sql("select SUM(cb.amount) as total from `tabConsumed Budget` cb where cb.cost_center=%s and cb.project=%s and cb.reference_date between %s and %s", (cost_center, project, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
		msg = " Project: <b> " + str(project) +"</b>, for Cost Center :  <b>" + str(cost_center) + "</b> level for <b>" + str(transaction_date)[0:4] + "</b>"
	else:
		bud_acc_dtl = frappe.get_doc("Account", budget_account)
		if bud_acc_dtl.has_linked_budget == 1:
			budget_account = bud_acc_dtl.linked_budget
		#Check for Ignore Budget
		if bud_acc_dtl.budget_check:
			return
		#Check if Budget Account is Centralized
		if bud_acc_dtl.centralized_budget:
			cost_center = bud_acc_dtl.cost_center
		else:
			cc_doc = frappe.get_doc("Cost Center", cost_center)
			if cc_doc.use_budget_from_parent:
				cost_center = cc_doc.parent_cost_center
		
		budget_amount = frappe.db.sql("select b.action_if_annual_budget_exceeded as action, \
						ba.budget_check, ba.budget_amount, b.deviation \
						from `tabBudget` b, `tabBudget Account` ba \
						where b.docstatus = 1 \
						and ba.parent = b.name and ba.account= '{}' \
						and b.fiscal_year = '{}' \
						and b.cost_center = '{}' ".format(budget_account, str(transaction_date)[0:4], cost_center), as_dict=True)
		if budget_amount:
			committed = frappe.db.sql("select SUM(cb.amount) as total from `tabCommitted Budget` cb where cb.account=%s and cb.cost_center=%s and cb.reference_date between %s and %s", (budget_account, cost_center, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
			consumed = frappe.db.sql("select SUM(cb.amount) as total from `tabConsumed Budget` cb where cb.account=%s and cb.cost_center=%s and cb.reference_date between %s and %s", (budget_account, cost_center, str(transaction_date)[0:4] + "-01-01", str(transaction_date)[0:4] + "-12-31"), as_dict=True)
		msg = "Account: <b>" + str(budget_account) + "</b> set at <b>" + str(cost_center) + "</b> level for <b>" + str(transaction_date)[0:4] + "</b>"

	if not budget_amount:
		frappe.throw("There is no budget allocated for " + str(msg))

	ig_or_stop = budget_amount and budget_amount[0].action or None
	ig_or_stop_gl = budget_amount and budget_amount[0].budget_check or None
	if ig_or_stop == "Ignore" or ig_or_stop_gl == "Ignore":
		return
	else:
		if consumed and committed:
			if flt(consumed[0].total) > flt(committed[0].total):
				committed = consumed
			total_consumed_amount = flt(committed[0].total) + flt(amount)
			total_budget_with_deviation = 0.00
			if budget_amount[0].deviation > 0:
				total_budget_with_deviation = flt(budget_amount[0].budget_amount) + flt(budget_amount[0].deviation * budget_amount[0].budget_amount)/100
			else:
				total_budget_with_deviation = budget_amount[0].budget_amount
			if flt(total_consumed_amount) > flt(total_budget_with_deviation):
				balance_budget = flt(budget_amount[0].budget_amount) - flt(committed[0].total)
				insufficient_amount = flt(amount) - flt(balance_budget)
				frappe.throw("Budget of Nu. {} insufficient in <b> {} </b>. Total Budget is Nu. {}, total Consumed and Committed is Nu. {}. Balance budget is Nu. {}. ".format(insufficient_amount, str(msg), flt(budget_amount[0].budget_amount), flt(committed[0].total), balance_budget))
		else:
			frappe.throw("There is no budget allocated for " + str(msg))

@frappe.whitelist()
def get_cc_warehouse(branch):
	cc = get_branch_cc(branch)
	return {"cc": cc, "wh": None}	

@frappe.whitelist()
def get_branch_warehouse(branch):
	cc = get_branch_cc(branch)
	wh = frappe.db.get_value("Cost Center", cc, "warehouse")
	if not wh:
		frappe.throw("No warehosue linked with your branch or cost center")
	return wh

@frappe.whitelist()
def get_branch_from_cost_center(cost_center):
	return frappe.db.get_value("Branch", {"cost_center": cost_center, "disabled": 0}, "name")

@frappe.whitelist()
def kick_users():
	from frappe.sessions import clear_all_sessions
	clear_all_sessions()
	frappe.msgprint("Kicked All Out!")

def get_cc_customer(cc):
	customer = frappe.db.get_value("Customer", {"cost_center": cc}, "name")
	if not customer:
		frappe.throw("No Customer found for the Cost Center")
	return customer

def send_mail_to_role_branch(branch, role, message, subject=None):
	if not subject:
		subject = "Message from ERP System"
	users = frappe.db.sql_list("select a.parent from tabUserRole a, tabDefaultValue b where a.parent = b.parent and b.defvalue = %s and b.defkey = 'Branch' and a.role = %s", (branch, role))
	try:
		frappe.sendmail(recipients=users, subject=subject, message=message)
	except:
		pass

def check_account_frozen(posting_date):
	acc_frozen_upto = frappe.db.get_value('Accounts Settings', None, 'acc_frozen_upto')
	if acc_frozen_upto:
		frozen_accounts_modifier = frappe.db.get_value( 'Accounts Settings', None,'frozen_accounts_modifier')
		if getdate(posting_date) <= getdate(acc_frozen_upto) \
				and not frozen_accounts_modifier in frappe.get_roles():
			frappe.throw(_("You are not authorized to add or update entries before {0}").format(formatdate(acc_frozen_upto)))

       
def sendmail(recipent, subject, message, sender=None):
	try:
		frappe.sendmail(recipients=recipent, sender=None, subject=subject, message=message)
	except:
		pass

def get_settings_value(setting_dt, company, field_name):
	value = frappe.db.sql("select {0} from `tab{1}` where company = '{2}'".format(field_name, setting_dt, company))
	return value and value[0][0] or None

###
# get_production_groups(group):
###
def get_production_groups(group):
	if not group:
		frappe.throw("Invalid Production Group")
	groups = []
	for a in frappe.db.sql("select item_code from `tabProduction Group Item` where parent = %s", group, as_dict=1):
		groups.append(str(a.item_code))
	return groups
                   
# Following code added by SHIV on 2021/05/13
def has_record_permission(doc, user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return True

	if frappe.db.exists("Employee", {"branch":doc.branch, "user_id": user}):
		return True
	elif frappe.db.sql("""select count(*)
   				from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
       			where e.user_id = '{user}'
          		and ab.employee = e.name
            	and bi.parent = ab.name
             	and bi.branch = "{branch}"
            """.format(user=user, branch=doc.branch))[0][0]:
		return True
	else:
		return False 

