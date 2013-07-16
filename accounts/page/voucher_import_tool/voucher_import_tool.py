from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import flt, comma_and, cstr
import webnotes.defaults

@webnotes.whitelist()
def get_template():
	"""download template"""
	template_type = webnotes.form_dict.get('type')
	
	doctypelist = webnotes.get_doctype("Journal Voucher")
	naming_options = doctypelist.get_options("naming_series")
	voucher_type = doctypelist.get_options("voucher_type")

	if template_type=="Two Accounts":
		extra_note = ""
		columns = '''"Naming Series","Voucher Type","Posting Date","Amount","Debit Account","Credit Account","Cost Center","Against Sales Invoice","Against Purchase Invoice","Against Journal Voucher","Remarks","Due Date","Ref Number","Ref Date"'''
	else:
		extra_note = '''
"5. Put the account head as Data label each in a new column"
"6. Put the Debit amount as +ve and Credit amount as -ve"'''
		columns = '''"Naming Series","Voucher Type","Posting Date","Cost Center","Against Sales Invoice","Against Purchase Invoice","Against Journal Voucher","Remarks","Due Date","Ref Number","Ref Date"'''
	
	
	webnotes.response['result'] = '''"Voucher Import: %(template_type)s"
"Each entry below will be a separate Journal Voucher."
"Note:"
"1. Dates in format: %(user_fmt)s"
"2. Cost Center is required for Income or Expense accounts"
"3. Naming Series Options: %(naming_options)s"
"4. Voucher Type Options: %(voucher_type)s"%(extra_note)s
"-------Common Values-----------"
"Company:",
"--------Data----------"
%(columns)s
''' % {
		"template_type": template_type,
		"user_fmt": webnotes.defaults.get_global_default('date_format'),
		"naming_options": naming_options.replace("\n", ", "),
		"voucher_type": voucher_type.replace("\n", ", "),
		"extra_note": extra_note,
		"columns": columns
	}
	webnotes.response['type'] = 'csv'
	webnotes.response['doctype'] = "Voucher-Import-%s" % template_type


@webnotes.whitelist()
def upload():
	messages = []
	try:
		from webnotes.utils.datautils import read_csv_content_from_uploaded_file
		rows = read_csv_content_from_uploaded_file()
	
		common_values = get_common_values(rows)
		company_abbr = webnotes.conn.get_value("Company", common_values.company, "abbr")
		
		if not company_abbr:
			webnotes.msgprint(_("Company is missing or entered incorrect value"), raise_exception=1)
		
		data, start_idx = get_data(rows, company_abbr, rows[0][0])
	except Exception, e:
		err_msg = webnotes.message_log and "<br>".join(webnotes.message_log) or cstr(e)
		messages.append("""<p style='color: red'>%s</p>""" % (err_msg or "No message"))
		webnotes.errprint(webnotes.getTraceback())
		webnotes.message_log = []
		return messages
		
	return import_vouchers(common_values, data, start_idx, rows[0][0])
	
	


def map_fields(field_list, source, target):
	for f in field_list:
		if ":" in f:
			target[f.split(":")[1]] = source.get(f.split(":")[0])
		else:
			target[f] = source.get(f)

def import_vouchers(common_values, data, start_idx, import_type):
	from webnotes.model.doc import Document
	from webnotes.model.bean import Bean
	from accounts.utils import get_fiscal_year
	from webnotes.utils.dateutils import parse_date
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
	try:
		jv = Document("Journal Voucher")
		
		webnotes.conn.begin()
		for i in xrange(len(data)):
			jv = Document("Journal Voucher")
			
			d = data[i][0]
			if import_type == "Voucher Import: Two Accounts" and flt(d.get("amount")) == 0:
				webnotes.message_log = ["Amount not specified"]
				raise Exception
			elif import_type == "Voucher Import: Multiple Accounts" and \
			 		(flt(d.get("total_debit")) == 0 or flt(d.get("total_credit")) == 0):
				webnotes.message_log = ["Total Debit and Total Credit amount can not be zero"]
				raise Exception
			else:
				d.posting_date = parse_date(d.posting_date)
				d.due_date = d.due_date and parse_date(d.due_date) or None
				
				if d.ref_number:
					if not d.ref_date:
						webnotes.msgprint(_("Ref Date is Mandatory if Ref Number is specified"), 
							raise_exception=1)
							
					d.ref_date = parse_date(d.ref_date)
				
				d.company = common_values.company
						
				map_fields(["voucher_type", "posting_date", "naming_series", 
					"remarks:user_remark", "ref_number:cheque_no", "ref_date:cheque_date",
					"is_opening", "due_date", "company"], d, jv.fields)

				jv.fiscal_year = get_fiscal_year(jv.posting_date)[0]

				details = []
				if import_type == "Voucher Import: Two Accounts":
					map_fields(["amount:total_debit", "amount:total_credit"], d, jv.fields)
					
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
				
					details = [detail1, detail2]
				elif import_type == "Voucher Import: Multiple Accounts":
					map_fields(["total_debit", "total_credit"], d, jv.fields)
					accounts = data[i][1]
					for acc in accounts:
						detail = Document("Journal Voucher Detail")
						detail.parent = True
						detail.parentfield = "entries"
						detail.account = acc
						detail.debit = flt(accounts[acc]) > 0 and flt(accounts[acc]) or 0
						detail.credit = flt(accounts[acc]) < 0 and -1*flt(accounts[acc]) or 0
						apply_cost_center_and_against_invoice(detail, d)
						details.append(detail)
								
				if not details:
					webnotes.message_log = ["""No accounts found. 
						If you entered accounts correctly, please check template once"""]
					raise Exception
					
				doclist = Bean([jv]+details)
				
				# validate datatype
				from core.page.data_import_tool.data_import_tool import check_record
				for d in doclist:
					check_record(d.fields, d.parenttype)
				
				doclist.submit()
			
				messages.append("""<p style='color: green'>[row #%s] 
					<a href=\"#Form/Journal Voucher/%s\">%s</a> imported</p>""" \
					% ((start_idx + 1) + i, jv.name, jv.name))
		webnotes.conn.commit()
	except Exception, e:
		webnotes.conn.rollback()
		err_msg = webnotes.message_log and "<br>".join(webnotes.message_log) or cstr(e)
		messages.append("""<p style='color: red'>[row #%s] %s failed: %s</p>"""
			% ((start_idx + 1) + i, jv.name or "", err_msg or "No message"))
		messages.append("<p style='color: red'>All transactions rolled back</p>")
		webnotes.errprint(webnotes.getTraceback())
		webnotes.message_log = []
			
	return messages

def get_common_values(rows):
	start = False
	common_values = webnotes._dict()
	
	for r in rows:
		if start:
			if r[0].startswith("---"):
				break
			common_values[r[0][:-1].replace(" ", "_").lower()] = r[1]
		if r[0]=="-------Common Values-----------":
			start = True

	return common_values
	
def get_data(rows, company_abbr, import_type):
	start_row = 0
	data = []
	start_row_idx = 0
	accounts = None
	for i in xrange(len(rows)):
		r = rows[i]
		if r[0]:
			if start_row and i >= start_row:
				if not start_row_idx: start_row_idx = i
				d, acc_dict = webnotes._dict(), webnotes._dict()
				for cidx in xrange(len(columns)):
					d[columns[cidx]] = r[cidx]
					
				if accounts:
					total_debit = total_credit = 0
					for acc_idx in xrange(len(accounts)):
						col_idx = len(columns) + acc_idx
						if flt(r[col_idx]) != 0:
							if not acc_dict.get(accounts[acc_idx]):
								acc_dict[accounts[acc_idx]] = 0
							acc_dict[accounts[acc_idx]] += flt(r[col_idx])
						if flt(r[col_idx]) > 0:
							total_debit += flt(r[col_idx])
						else:
							total_credit += abs(flt(r[col_idx]))
							
					d['total_debit'] = total_debit
					d['total_credit'] = total_credit
				
				data.append([d, acc_dict])
				

			if r[0]=="--------Data----------":
				start_row = i+2
				
				# check for empty columns
				empty_columns = [j+1 for j, c in enumerate(rows[i+1]) if not c]
				if empty_columns:
					raise Exception, """Column No(s). %s %s empty. \
						Please remove them and try again.""" % (comma_and(empty_columns),
						len(empty_columns)==1 and "is" or "are")

				columns = [c.replace(" ", "_").lower() for c in rows[i+1] 
					if not c.endswith(" - " + company_abbr)]
					
				if import_type == "Voucher Import: Multiple Accounts":
					accounts = [c for c in rows[i+1] if c.endswith(" - " + company_abbr)]

					if not accounts:
						webnotes.msgprint(_("""No Account found in csv file, 
							May be company abbreviation is not correct"""), raise_exception=1)

					if accounts and (len(columns) != rows[i+1].index(accounts[0])):
						webnotes.msgprint(_("""All account columns should be after \
							standard columns and on the right.
							If you entered it properly, next probable reason \
							could be wrong account name.
							Please rectify it in the file and try again."""), raise_exception=1)
				
	return data, start_row_idx