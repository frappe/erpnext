from __future__ import unicode_literals
import webnotes
from webnotes.utils import formatdate

@webnotes.whitelist()
def get_template_multiple():
	"""download single template"""
	from webnotes.model.doctype import get_field_property
	naming_options = get_field_property("Journal Voucher", "naming_series", "options")
	voucher_type = get_field_property("Journal Voucher", "voucher_type", "options")
	
	webnotes.response['result'] = '''"Voucher Import :Multiple"
"Each entry below will be a separate Journal Voucher."
"Note:"
"1. Dates in format: %(user_fmt)s"
"2. Cost Center is required for Income or Expense accounts"
"3. Naming Series Options: %(naming_options)s"
"4. Voucher Type Options: %(voucher_type)s"
"-------Common Values-----------"
"Company:","%(default_company)s"
"--------Data----------"
"Naming Series","Voucher Type","Posting Date","Amount","Debit Account","Credit Account","Cost Center","Against Sales Invoice","Against Purchase Invoice","Against Journal Voucher","Remarks","Due Date","Ref Number","Ref Date"
''' % {
		"user_fmt": webnotes.conn.get_value('Control Panel', None, 'date_format'),
		"default_company": webnotes.conn.get_default("company"),
		"naming_options": naming_options.replace("\n", ", "),
		"voucher_type": voucher_type.replace("\n", ", ")
	}
	webnotes.response['type'] = 'csv'
	webnotes.response['doctype'] = "Voucher-Import-Single"

@webnotes.whitelist()
def upload():
	from webnotes.utils.datautils import read_csv_content_from_uploaded_file
	rows = read_csv_content_from_uploaded_file()

	common_values = get_common_values(rows)
	data = get_data(rows)
	
	if rows[0][0]=="Voucher Import :Single":
		return import_single(common_values, data)
	else:
		return import_multiple(common_values, data)

def map_fields(field_list, source, target):
	for f in field_list:
		if ":" in f:
			target[f.split(":")[1]] = source.get(f.split(":")[0])
		else:
			target[f] = source.get(f)

def import_multiple(common_values, data):
	from webnotes.model.doc import Document
	from webnotes.model.doclist import DocList
	from webnotes.model.code import get_obj
	from accounts.utils import get_fiscal_year_from_date
	from webnotes.utils.dateutils import user_to_str

	messages = []
		
	def get_account_details(account):
		acc_details = webnotes.conn.sql("""select is_pl_account, 
			master_name from tabAccount where name=%s""", account, as_dict=1)
		if not acc_details:
			webnotes.msgprint("%s is not an Account" % account, raise_exception=1)
		return acc_details[0]

	def apply_cost_center_and_against_invoice(detail, d):
		account = get_account_details(detail.account)

		if account.is_pl_account=="Yes":
			detail.cost_center = d.cost_center
		
		if account.master_name:
			map_fields(["against_sales_invoice:against_invoice", 
				"against_purhase_invoice:against_voucher", 
				"against_journal_voucher:against_jv"], d, detail.fields)
	
	webnotes.conn.commit()
	for i in xrange(len(data)):
		d = data[i]
		jv = webnotes.DictObj()

		try:
			d.posting_date = user_to_str(d.posting_date)
			d.due_date = user_to_str(d.due_date)
			d.ref_date = user_to_str(d.ref_date)
			d.company = common_values.company
						
			jv = Document("Journal Voucher")
			map_fields(["voucher_type", "posting_date", "naming_series", "remarks:remark",
				"ref_no:cheque_no", "ref_date:cheque_date", "is_opening",
				"amount:total_debit", "amount:total_credit", "due_date", "company"], d, jv.fields)

			jv.fiscal_year = get_fiscal_year_from_date(jv.posting_date)

			detail1 = Document("Journal Voucher Detail")
			detail1.parent = True
			detail1.parentfield = "entries"
			map_fields(["debit_account:account","amount:debit"], d, detail1.fields)
			apply_cost_center_and_against_invoice(detail1, d)
		

			detail2 = Document("Journal Voucher Detail")
			detail2.parent = True
			detail2.parentfield = "entries"
			map_fields(["credit_account:account","amount:credit"], d, detail2.fields)
			apply_cost_center_and_against_invoice(detail2, d)
			
			webnotes.conn.begin()
			doclist = DocList([jv, detail1, detail2])
			doclist.submit()
			webnotes.conn.commit()
			
			messages.append("<p style='color: green'>[row #%s] %s imported</p>" \
				% (i, jv.name))
			
		except Exception, e:
			webnotes.conn.rollback()
			messages.append("<p style='color: red'>[row #%s] %s failed: %s</p>" \
				% (i, jv.name, webnotes.message_log and webnotes.message_log[0] or "No message"))
			webnotes.errprint(webnotes.getTraceback())

		webnotes.message_log = []
			
	return messages

def get_common_values(rows):
	start = False
	common_values = webnotes.DictObj()
	
	for r in rows:
		if start:
			if r[0].startswith("---"):
				break
			common_values[r[0][:-1].replace(" ", "_").lower()] = r[1]
		if r[0]=="-------Common Values-----------":
			start = True

	return common_values
	
def get_data(rows):
	start_row = 0
	data = []
	
	for i in xrange(len(rows)):
		r = rows[i]
		if r[0]:
			if start_row and i >= start_row:
				d = webnotes.DictObj()
				for cidx in xrange(len(columns)):
					d[columns[cidx]] = r[cidx]
				data.append(d)

			if r[0]=="--------Data----------":
				start_row = i+2
				columns = [c.replace(" ", "_").lower() for c in rows[i+1]]
	return data
	
@webnotes.whitelist()
def get_template_single():
	"""download single template"""
	
	webnotes.response['result'] = '''"Voucher Import :Single"
"All entries below will be uploaded in one Journal Voucher."
"Enter details below:"
"-------Common Values-----------"
"Voucher Series:",
"Voucher Type:",
"Posting Date:","%(posting_date)s"
"Remarks:",
"Is Opening:","No"
"Company:","%(default_company)s"
"------------------"
"Enter rows below headings:"
"Cost Center is required for Income or Expense accounts"
"--------Data----------"
"Account","Cost Center","Debit Amount","Credit Amount","Against Sales Invoice","Against Purchase Invoice","Against Journal Voucher"
''' % {
		"posting_date": formatdate(),
		"default_company": webnotes.conn.get_default("company")
	}
	webnotes.response['type'] = 'csv'
	webnotes.response['doctype'] = "Voucher-Import-Single"
