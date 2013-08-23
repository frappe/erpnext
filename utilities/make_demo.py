# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes, os, datetime
import webnotes.utils
from webnotes.utils import random_string
from webnotes.widgets import query_report
import random
import json

webnotes.session = webnotes._dict({"user":"Administrator"})
from core.page.data_import_tool.data_import_tool import upload

# fix price list
# fix fiscal year

company = "Wind Power LLC"
company_abbr = "WP"
country = "United States"
currency = "USD"
time_zone = "America/New York"
start_date = '2010-01-01'
bank_name = "Citibank"
runs_for = 20
prob = {
	"default": { "make": 0.6, "qty": (1,5) },
	"Sales Order": { "make": 0.4, "qty": (1,3) },
	"Purchase Order": { "make": 0.7, "qty": (1,15) },
	"Purchase Receipt": { "make": 0.7, "qty": (1,15) },
}

def make(reset=False):
	webnotes.connect()
	#webnotes.print_messages = True
	webnotes.mute_emails = True
	webnotes.rollback_on_exception = True
	
	if reset:
		setup()
	simulate()
	
def setup():
	install()
	complete_setup()
	make_customers_suppliers_contacts()
	make_items()
	make_users_and_employees()
	make_bank_account()
	# make_opening_stock()
	# make_opening_accounts()

def simulate():
	current_date = None
	for i in xrange(runs_for):
		if not current_date:
			# get last stock ledger posting date or use default
			last_posting = webnotes.conn.sql("""select max(posting_date) from `tabStock Ledger Entry`""")
			if last_posting[0][0]:
				current_date = webnotes.utils.add_days(last_posting[0][0], 1)
			else:
				current_date = webnotes.utils.getdate(start_date)
		else:
			current_date = webnotes.utils.add_days(current_date, 1)
		
		print current_date.strftime("%Y-%m-%d")
		
		if current_date.weekday() in (5, 6):
			continue

		run_sales(current_date)
		run_purchase(current_date)
		run_manufacturing(current_date)
		run_stock(current_date)
		run_accounts(current_date)
		
def run_sales(current_date):
	if can_make("Quotation"):
		for i in xrange(how_many("Quotation")):
			make_quotation(current_date)
					
	if can_make("Sales Order"):
		for i in xrange(how_many("Sales Order")):
			make_sales_order(current_date)

def run_accounts(current_date):
	if can_make("Sales Invoice"):
		from selling.doctype.sales_order.sales_order import make_sales_invoice
		report = "Ordered Items to be Billed"
		for so in list(set([r[0] for r in query_report.run(report)["result"] if r[0]!="Total"]))[:how_many("Sales Invoice")]:
			si = webnotes.bean(make_sales_invoice(so))
			si.doc.posting_date = current_date
			si.insert()
			si.submit()
			webnotes.conn.commit()

	if can_make("Purchase Invoice"):
		from stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
		report = "Received Items to be Billed"
		for pr in list(set([r[0] for r in query_report.run(report)["result"] if r[0]!="Total"]))[:how_many("Purchase Invoice")]:
			pi = webnotes.bean(make_purchase_invoice(pr))
			pi.doc.posting_date = current_date
			pi.doc.bill_no = random_string(6)
			pi.insert()
			pi.submit()
			webnotes.conn.commit()
			
	if can_make("Payment Received"):
		from accounts.doctype.journal_voucher.journal_voucher import get_payment_entry_from_sales_invoice
		report = "Accounts Receivable"
		for si in list(set([r[4] for r in query_report.run(report, {"report_date": current_date })["result"] if r[3]=="Sales Invoice"]))[:how_many("Payment Received")]:
			jv = webnotes.bean(get_payment_entry_from_sales_invoice(si))
			jv.doc.posting_date = current_date
			jv.doc.cheque_no = random_string(6)
			jv.doc.cheque_date = current_date
			jv.insert()
			jv.submit()
			webnotes.conn.commit()
			
	if can_make("Payment Made"):
		from accounts.doctype.journal_voucher.journal_voucher import get_payment_entry_from_purchase_invoice
		report = "Accounts Payable"
		for pi in list(set([r[4] for r in query_report.run(report, {"report_date": current_date })["result"] if r[3]=="Purchase Invoice"]))[:how_many("Payment Made")]:
			jv = webnotes.bean(get_payment_entry_from_purchase_invoice(pi))
			jv.doc.posting_date = current_date
			jv.doc.cheque_no = random_string(6)
			jv.doc.cheque_date = current_date
			jv.insert()
			jv.submit()
			webnotes.conn.commit()

def run_stock(current_date):
	# make purchase requests
	if can_make("Purchase Receipt"):
		from buying.doctype.purchase_order.purchase_order import make_purchase_receipt
		report = "Purchase Order Items To Be Received"
		for po in list(set([r[0] for r in query_report.run(report)["result"] if r[0]!="Total"]))[:how_many("Purchase Receipt")]:
			pr = webnotes.bean(make_purchase_receipt(po))
			pr.doc.posting_date = current_date
			pr.doc.fiscal_year = "2010"
			pr.insert()
			pr.submit()
			webnotes.conn.commit()
	
	# make delivery notes (if possible)
	if can_make("Delivery Note"):
		from selling.doctype.sales_order.sales_order import make_delivery_note
		from stock.stock_ledger import NegativeStockError
		from stock.doctype.stock_ledger_entry.stock_ledger_entry import SerialNoRequiredError, SerialNoQtyError
		report = "Ordered Items To Be Delivered"
		for so in list(set([r[0] for r in query_report.run(report)["result"] if r[0]!="Total"]))[:how_many("Delivery Note")]:
			dn = webnotes.bean(make_delivery_note(so))
			dn.doc.posting_date = current_date
			dn.doc.fiscal_year = "2010"
			dn.insert()
			try:
				dn.submit()
				webnotes.conn.commit()
			except NegativeStockError: pass
			except SerialNoRequiredError: pass
			except SerialNoQtyError: pass
	
	# try submitting existing
	for dn in webnotes.conn.get_values("Delivery Note", {"docstatus": 0}, "name"):
		b = webnotes.bean("Delivery Note", dn[0])
		b.submit()
		webnotes.conn.commit()
	
def run_purchase(current_date):
	# make material requests for purchase items that have negative projected qtys
	if can_make("Material Request"):
		report = "Items To Be Requested"
		for row in query_report.run(report)["result"][:how_many("Material Request")]:
			mr = webnotes.new_bean("Material Request")
			mr.doc.material_request_type = "Purchase"
			mr.doc.transaction_date = current_date
			mr.doc.fiscal_year = "2010"
			mr.doclist.append({
				"doctype": "Material Request Item",
				"parentfield": "indent_details",
				"schedule_date": webnotes.utils.add_days(current_date, 7),
				"item_code": row[0],
				"qty": -row[-1]
			})
			mr.insert()
			mr.submit()
	
	# make supplier quotations
	if can_make("Supplier Quotation"):
		from stock.doctype.material_request.material_request import make_supplier_quotation
		report = "Material Requests for which Supplier Quotations are not created"
		for row in query_report.run(report)["result"][:how_many("Supplier Quotation")]:
			if row[0] != "Total":
				sq = webnotes.bean(make_supplier_quotation(row[0]))
				sq.doc.transaction_date = current_date
				sq.doc.fiscal_year = "2010"
				sq.insert()
				sq.submit()
				webnotes.conn.commit()
		
	# make purchase orders
	if can_make("Purchase Order"):
		from stock.doctype.material_request.material_request import make_purchase_order
		report = "Requested Items To Be Ordered"
		for row in query_report.run(report)["result"][:how_many("Purchase Order")]:
			if row[0] != "Total":
				po = webnotes.bean(make_purchase_order(row[0]))
				po.doc.transaction_date = current_date
				po.doc.fiscal_year = "2010"
				po.insert()
				po.submit()
				webnotes.conn.commit()
			
def run_manufacturing(current_date):
	from stock.stock_ledger import NegativeStockError
	from stock.doctype.stock_entry.stock_entry import IncorrectValuationRateError, DuplicateEntryForProductionOrderError

	ppt = webnotes.bean("Production Planning Tool", "Production Planning Tool")
	ppt.doc.company = company
	ppt.doc.use_multi_level_bom = 1
	ppt.doc.purchase_request_for_warehouse = "Stores - WP"
	ppt.run_method("get_open_sales_orders")
	ppt.run_method("get_items_from_so")
	ppt.run_method("raise_production_order")
	ppt.run_method("raise_purchase_request")
	webnotes.conn.commit()
	
	# submit production orders
	for pro in webnotes.conn.get_values("Production Order", {"docstatus": 0}, "name"):
		b = webnotes.bean("Production Order", pro[0])
		b.doc.wip_warehouse = "Work in Progress - WP"
		b.submit()
		webnotes.conn.commit()
		
	# submit material requests
	for pro in webnotes.conn.get_values("Material Request", {"docstatus": 0}, "name"):
		b = webnotes.bean("Material Request", pro[0])
		b.submit()
		webnotes.conn.commit()
	
	# stores -> wip
	if can_make("Stock Entry for WIP"):		
		for pro in query_report.run("Open Production Orders")["result"][:how_many("Stock Entry for WIP")]:
			make_stock_entry_from_pro(pro[0], "Material Transfer", current_date)
		
	# wip -> fg
	if can_make("Stock Entry for FG"):		
		for pro in query_report.run("Production Orders in Progress")["result"][:how_many("Stock Entry for FG")]:
			make_stock_entry_from_pro(pro[0], "Manufacture/Repack", current_date)

	# try posting older drafts (if exists)
	for st in webnotes.conn.get_values("Stock Entry", {"docstatus":0}, "name"):
		try:
			webnotes.bean("Stock Entry", st[0]).submit()
			webnotes.conn.commit()
		except NegativeStockError: pass
		except IncorrectValuationRateError: pass
		except DuplicateEntryForProductionOrderError: pass

def make_stock_entry_from_pro(pro_id, purpose, current_date):
	from manufacturing.doctype.production_order.production_order import make_stock_entry
	from stock.stock_ledger import NegativeStockError
	from stock.doctype.stock_entry.stock_entry import IncorrectValuationRateError, DuplicateEntryForProductionOrderError

	st = webnotes.bean(make_stock_entry(pro_id, purpose))
	st.doc.posting_date = current_date
	st.doc.fiscal_year = "2010"
	st.doc.expense_adjustment_account = "Stock in Hand - WP"
	try:
		st.insert()
		webnotes.conn.commit()
		st.submit()
		webnotes.conn.commit()
	except NegativeStockError: pass
	except IncorrectValuationRateError: pass
	except DuplicateEntryForProductionOrderError: pass

def make_quotation(current_date):
	b = webnotes.bean([{
		"creation": current_date,
		"doctype": "Quotation",
		"quotation_to": "Customer",
		"customer": get_random("Customer"),
		"order_type": "Sales",
		"transaction_date": current_date,
		"fiscal_year": "2010"
	}])
	
	add_random_children(b, {
		"doctype": "Quotation Item", 
		"parentfield": "quotation_details", 
	}, rows=3, randomize = {
		"qty": (1, 5),
		"item_code": ("Item", {"is_sales_item": "Yes"})
	}, unique="item_code")
	
	b.insert()
	webnotes.conn.commit()
	b.submit()
	webnotes.conn.commit()
	
def make_sales_order(current_date):
	q = get_random("Quotation", {"status": "Submitted"})
	if q:
		from selling.doctype.quotation.quotation import make_sales_order
		so = webnotes.bean(make_sales_order(q))
		so.doc.transaction_date = current_date
		so.doc.delivery_date = webnotes.utils.add_days(current_date, 10)
		so.insert()
		webnotes.conn.commit()
		so.submit()
		webnotes.conn.commit()
	
def add_random_children(bean, template, rows, randomize, unique=None):
	for i in xrange(random.randrange(1, rows)):
		d = template.copy()
		for key, val in randomize.items():
			if isinstance(val[0], basestring):
				d[key] = get_random(*val)
			else:
				d[key] = random.randrange(*val)
		
		if unique:
			if not bean.doclist.get({"doctype": d["doctype"], unique:d[unique]}):
				bean.doclist.append(d)
		else:
			bean.doclist.append(d)

def get_random(doctype, filters=None):
	condition = []
	if filters:
		for key, val in filters.items():
			condition.append("%s='%s'" % (key, val))
	if condition:
		condition = " where " + " and ".join(condition)
	else:
		condition = ""
		
	out = webnotes.conn.sql("""select name from `tab%s` %s
		order by RAND() limit 0,1""" % (doctype, condition))

	return out and out[0][0] or None

def can_make(doctype):
	return random.random() < prob.get(doctype, prob["default"])["make"]

def how_many(doctype):
	return random.randrange(*prob.get(doctype, prob["default"])["qty"])

def install():
	print "Creating Fresh Database..."
	from webnotes.install_lib.install import Installer
	inst = Installer('root')
	inst.import_from_db("demo", verbose = 1)

def complete_setup():
	print "Complete Setup..."
	webnotes.get_obj("Setup Control").setup_account({
		"first_name": "Test",
		"last_name": "User",
		"fy_start": "1st Jan",
		"industry": "Manufacturing",
		"company_name": company,
		"company_abbr": company_abbr,
		"currency": currency,
		"timezone": time_zone,
		"country": country
	})

	import_data("Fiscal_Year")
	
def make_items():
	import_data("Item")
	import_data("BOM", submit=True)
	
def make_customers_suppliers_contacts():
	import_data(["Customer", "Supplier", "Contact", "Address", "Lead"])

def make_users_and_employees():
	webnotes.conn.set_value("HR Settings", None, "emp_created_by", "Naming Series")
	webnotes.conn.commit()
	
	import_data(["Profile", "Employee", "Salary_Structure"])

def make_bank_account():
	ba = webnotes.bean({
		"doctype": "Account",
		"account_name": bank_name,
		"account_type": "Bank or Cash",
		"group_or_ledger": "Ledger",
		"parent_account": "Bank Accounts - " + company_abbr,
		"company": company
	}).insert()
	
	webnotes.set_value("Company", company, "default_bank_account", ba.doc.name)

def import_data(dt, submit=False):
	if not isinstance(dt, (tuple, list)):
		dt = [dt]
	
	for doctype in dt:
		print "Importing", doctype.replace("_", " "), "..."
		webnotes.form_dict = {}
		if submit:
			webnotes.form_dict["params"] = json.dumps({"_submit": 1})
		webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", doctype+".csv")
		upload()

if __name__=="__main__":
	make()