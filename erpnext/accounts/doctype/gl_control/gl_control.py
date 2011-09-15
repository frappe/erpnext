# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists

# -----------------------------------------------------------------------------------------
from utilities.transaction_base import TransactionBase

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d, dl
		self.entries = []

	# Get Company List
	# ----------------
	def get_companies(self,arg=''):
		#d = get_defaults()
		ret = sql("select name, abbr from tabCompany where docstatus != 2")
		#pl = {}
		#for r in ret:
		#	inc = get_value('Account','Income - '+r[1], 'balance')
		#	exp = get_value('Account','Expenses - '+r[1], 'balance')
		#	pl[r[0]] = flt(flt(inc) - flt(exp))
		return {'cl':[r[0] for r in ret]}#, 'pl':pl}

	def get_company_currency(self,arg=''):
		dcc = TransactionBase().get_company_currency(arg)
		return dcc

	# Get current balance
	# --------------------
	def get_bal(self,arg):
		ac, fy = arg.split('~~~')
		det = sql("select t1.balance, t2.debit_or_credit from `tabAccount Balance` t1, `tabAccount` t2 where t1.period = %s and t2.name=%s and t1.account = t2.name", (fy, ac))
		bal = det and flt(det[0][0]) or 0
		dr_or_cr = det and flt(det[0][1]) or ''
		return fmt_money(bal) + ' ' + dr_or_cr

	def get_period_balance(self,arg):
		acc, f, t = arg.split('~~~')
		c, fy = '', get_defaults()['fiscal_year']

		det = sql("select debit_or_credit, lft, rgt, is_pl_account from tabAccount where name=%s", acc)
		if f: c += (' and t1.posting_date >= "%s"' % f)
		if t: c += (' and t1.posting_date <= "%s"' % t)
		bal = sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) from `tabGL Entry` t1 where t1.account='%s' and ifnull(is_opening, 'No') = 'No' %s" % (acc, c))
		bal = bal and flt(bal[0][0]) or 0

		if det[0][0] != 'Debit':
			bal = (-1) * bal

		# add opening for balance sheet accounts
		if det[0][3] == 'No':
			opening = flt(sql("select opening from `tabAccount Balance` where account=%s and period=%s", (acc, fy))[0][0])
			bal = bal + opening

		return flt(bal)


	def get_period_difference(self,arg, cost_center =''):
		# used in General Ledger Page Report
		# used for Budget where cost center passed as extra argument
		acc, f, t = arg.split('~~~')
		c, fy = '', get_defaults()['fiscal_year']

		det = sql("select debit_or_credit, lft, rgt, is_pl_account from tabAccount where name=%s", acc)
		if f: c += (' and t1.posting_date >= "%s"' % f)
		if t: c += (' and t1.posting_date <= "%s"' % t)
		if cost_center: c += (' and t1.cost_center = "%s"' % cost_center)
		bal = sql("select sum(ifnull(t1.debit,0))-sum(ifnull(t1.credit,0)) from `tabGL Entry` t1 where t1.account='%s' %s" % (acc, c))
		bal = bal and flt(bal[0][0]) or 0

		if det[0][0] != 'Debit':
			bal = (-1) * bal

		return flt(bal)

	# Get Children (for tree)
	# -----------------------
	def get_cl(self, arg):

		fy = get_defaults()['fiscal_year']
		parent, parent_acc_name, company, type = arg.split(',')

		# get children account details
		if type=='Account':

			if parent=='Root Node':

				cl = sql("select t1.name, t1.group_or_ledger, t1.debit_or_credit, t2.balance, t1.account_name from tabAccount t1, `tabAccount Balance` t2 where ifnull(t1.parent_account, '') = '' and t1.docstatus != 2 and t1.company=%s and t1.name = t2.account and t2.period = %s order by t1.name asc", (company, fy),as_dict=1)
			else:
				cl = sql("select t1.name, t1.group_or_ledger, t1.debit_or_credit, t2.balance, t1.account_name from tabAccount t1, `tabAccount Balance` t2 where ifnull(t1.parent_account, '')=%s and t1.docstatus != 2 and t1.company=%s and t1.name = t2.account and t2.period = %s order by t1.name asc",(parent, company, fy) ,as_dict=1)

			# remove Decimals
			for c in cl: c['balance'] = flt(c['balance'])

		# get children cost center details
		elif type=='Cost Center':
			if parent=='Root Node':
				cl = sql("select name,group_or_ledger, cost_center_name from `tabCost Center`	where ifnull(parent_cost_center, '')='' and docstatus != 2 and company_name=%s order by name asc",(company),as_dict=1)
			else:
				cl = sql("select name,group_or_ledger,cost_center_name from `tabCost Center` where ifnull(parent_cost_center, '')=%s and docstatus != 2 and company_name=%s order by name asc",(parent,company),as_dict=1)
		return {'parent':parent, 'parent_acc_name':parent_acc_name, 'cl':cl}

	# Add a new account
	# -----------------
	def add_ac(self,arg):
		arg = eval(arg)
		ac = Document('Account')
		for d in arg.keys():
			ac.fields[d] = arg[d]
		ac.old_parent = ''
		ac_obj = get_obj(doc=ac)
		ac_obj.validate()
		ac_obj.doc.save(1)
		ac_obj.on_update()

		return ac_obj.doc.name

	# Add a new cost center
	#----------------------
	def add_cc(self,arg):
		arg = eval(arg)
		cc = Document('Cost Center')
		# map fields
		for d in arg.keys():
			cc.fields[d] = arg[d]
		# map company abbr
		other_info = sql("select company_abbr from `tabCost Center` where name='%s'"%arg['parent_cost_center'])
		cc.company_abbr = other_info and other_info[0][0] or arg['company_abbr']

		cc_obj = get_obj(doc=cc)
		cc_obj.validate()
		cc_obj.doc.save(1)
		cc_obj.on_update()

		return cc_obj.doc.name


	# Get field values from the voucher
	#------------------------------------------
	def get_val(self, src, d, parent=None):
		if not src:
			return None
		if src.startswith('parent:'):
			return parent.fields[src.split(':')[1]]
		elif src.startswith('value:'):
			return eval(src.split(':')[1])
		elif src:
			return d.fields.get(src)

	def check_if_in_list(self, le):
		for e in self.entries:
			if e.account == le.account and (cstr(e.against_voucher)==cstr(le.against_voucher)) and (cstr(e.against_voucher_type)==cstr(le.against_voucher_type)) and (cstr(e.cost_center)==cstr(le.cost_center)):
				return [e]
		return 0

	# Make a dictionary(le) for every gl entry and append to a list(self.entries)
	#----------------------------------------------------------------------------
	def make_single_entry(self,parent,d,le_map,cancel, merge_entries):
		if self.get_val(le_map['account'], d, parent) and (self.get_val(le_map['debit'], d, parent) or self.get_val(le_map['credit'], d, parent)):
			flist = ['account','cost_center','against','debit','credit','remarks','voucher_type','voucher_no','transaction_date','posting_date','fiscal_year','against_voucher','against_voucher_type','company','is_opening', 'aging_date']

			# Check budget before gl entry
			#check budget only if account is expense account
			is_expense_acct = sql("select name from tabAccount where is_pl_account='Yes' and debit_or_credit='Debit' and name=%s",self.get_val(le_map['account'], d, parent))
			if is_expense_acct and self.get_val(le_map['cost_center'], d, parent):
				get_obj('Budget Control').check_budget([self.get_val(le_map[k], d, parent) for k in flist if k in ['account','cost_center','debit','credit','posting_date','fiscal_year','company']],cancel)

			# Create new GL entry object and map values
			le = Document('GL Entry')
			for k in flist:
				le.fields[k] = self.get_val(le_map[k], d, parent)

			# if there is already an entry in this account then just add it to that entry
			same_head = self.check_if_in_list(le)
			if same_head and merge_entries:
				same_head = same_head[0]
				same_head.debit	= flt(same_head.debit)	+ flt(le.debit)
				same_head.credit = flt(same_head.credit) + flt(le.credit)
			else:
				self.entries.append(le)

	# Save GL Entries
	# ----------------
	def save_entries(self, cancel, adv_adj, update_outstanding):
		for le in self.entries:
			# cancel
			if cancel or flt(le.debit) < 0 or flt(le.credit) < 0:
				tmp=le.debit
				le.debit, le.credit = abs(flt(le.credit)), abs(flt(tmp))


			le_obj = get_obj(doc=le)
			# validate except on_cancel
			if not cancel:
				le_obj.validate()

			# save
			le.save(1)
			le_obj.on_update(adv_adj, cancel, update_outstanding)

			# update total debit / credit
			self.td += flt(le.debit)
			self.tc += flt(le.credit)

	# Make Multiple Entries
	# ---------------------
	def make_gl_entries(self, doc, doclist, cancel=0, adv_adj = 0, use_mapper='', merge_entries = 1, update_outstanding='Yes'):
		# get entries
		le_map_list = sql("select * from `tabGL Mapper Detail` where parent = %s", use_mapper or doc.doctype, as_dict=1)
		self.td, self.tc = 0.0, 0.0
		for le_map in le_map_list:
			if le_map['table_field']:
				for d in getlist(doclist,le_map['table_field']):
					# purchase_tax_details is the table of other charges in purchase cycle
					if le_map['table_field'] != 'purchase_tax_details' or (le_map['table_field'] == 'purchase_tax_details' and d.fields.get('category') != 'For Valuation'):
						self.make_single_entry(doc,d,le_map,cancel, merge_entries)
			else:
				self.make_single_entry(None,doc,le_map,cancel, merge_entries)

		# save entries
		self.save_entries(cancel, adv_adj, update_outstanding)

		# check total debit / credit
		# Due to old wrong entries (total debit != total credit) some voucher could be cancelled
		if abs(self.td - self.tc) > 0.001 and not cancel:
			msgprint("Debit and Credit not equal for this voucher: Diff (Debit) is %s" % (self.td-self.tc))
			raise Exception

		# set as cancelled
		if cancel:
			vt, vn = self.get_val(le_map['voucher_type'],	doc, doc), self.get_val(le_map['voucher_no'],	doc, doc)
			sql("update `tabGL Entry` set is_cancelled='Yes' where voucher_type=%s and voucher_no=%s", (vt, vn))

	# Get account balance on any date
	# -------------------------------
	def get_as_on_balance(self, account_name, fiscal_year, as_on, credit_or_debit, lft, rgt):
		# initialization
		det = sql("select start_date, opening from `tabAccount Balance` where period = %s and account = %s", (fiscal_year, account_name))
		from_date, opening, debit_bal, credit_bal, closing_bal = det and det[0][0] or getdate(nowdate()), det and flt(det[0][1]) or 0, 0, 0, det and flt(det[0][1]) or 0

		# prev month closing
		prev_month_det = sql("select end_date, debit, credit, balance from `tabAccount Balance` where account = %s and end_date <= %s and fiscal_year = %s order by end_date desc limit 1", (account_name, as_on, fiscal_year))
		if prev_month_det:
			from_date = getdate(add_days(prev_month_det[0][0].strftime('%Y-%m-%d'), 1))
			opening = 0
			debit_bal = flt(prev_month_det[0][1])
			credit_bal = flt(prev_month_det[0][2])
			closing_bal = flt(prev_month_det[0][3])

		# curr month transaction
		if getdate(as_on) >= from_date:
			curr_month_bal = sql("select SUM(t1.debit), SUM(t1.credit) from `tabGL Entry` t1, `tabAccount` t2 WHERE t1.posting_date >= %s AND t1.posting_date <= %s and ifnull(t1.is_opening, 'No') = 'No' AND t1.account = t2.name AND t2.lft >= %s AND t2.rgt <= %s and ifnull(t1.is_cancelled, 'No') = 'No'", (from_date, as_on, lft, rgt))
			curr_debit_amt, curr_credit_amt = flt(curr_month_bal[0][0]), flt(curr_month_bal[0][1])
			debit_bal = curr_month_bal and debit_bal + curr_debit_amt or debit_bal
			credit_bal = curr_month_bal and credit_bal + curr_credit_amt or credit_bal

			if credit_or_debit == 'Credit':
				curr_debit_amt, curr_credit_amt = -1*flt(curr_month_bal[0][0]), -1*flt(curr_month_bal[0][1])
			closing_bal = closing_bal + curr_debit_amt - curr_credit_amt

		return flt(debit_bal), flt(credit_bal), flt(closing_bal)


	# ADVANCE ALLOCATION
	#-------------------
	def get_advances(self, obj, account_head, table_name,table_field_name, dr_or_cr):
		jv_detail = sql("select t1.name, t1.remark, t2.%s, t2.name, t1.ded_amount from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 where t1.name = t2.parent and (t2.against_voucher is null or t2.against_voucher = '') and (t2.against_invoice is null or t2.against_invoice = '') and (t2.against_jv is null or t2.against_jv = '') and t2.account = '%s' and t2.is_advance = 'Yes' and t1.docstatus = 1 order by t1.voucher_date " % (dr_or_cr,account_head))
		# clear advance table
		obj.doc.clear_table(obj.doclist,table_field_name)
		# Create advance table
		for d in jv_detail:
			add = addchild(obj.doc, table_field_name, table_name, 1, obj.doclist)
			add.journal_voucher = d[0]
			add.jv_detail_no = d[3]
			add.remarks = d[1]
			add.advance_amount = flt(d[2])
			add.allocate_amount = 0
			if table_name == 'Advance Allocation Detail':
				add.tds_amount = flt(d[4])

	# Clear rows which is not adjusted
	#-------------------------------------
	def clear_advances(self, obj,table_name,table_field_name):
		for d in getlist(obj.doclist,table_field_name):
			if not flt(d.allocated_amount):
				sql("update `tab%s` set parent = '' where name = '%s' and parent = '%s'" % (table_name, d.name, d.parent))
				d.parent = ''

	# Update aginst document in journal voucher
	#------------------------------------------
	def update_against_document_in_jv(self, obj, table_field_name, against_document_no, against_document_doctype, account_head, dr_or_cr,doctype):
		for d in getlist(obj.doclist, table_field_name):
			self.validate_jv_entry(d, account_head, dr_or_cr)
			if flt(d.advance_amount) == flt(d.allocated_amount):
				# cancel JV
				jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children=1)
				get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =1, adv_adj =1)

				# update ref in JV Detail
				sql("update `tabJournal Voucher Detail` set %s = '%s' where name = '%s'" % (doctype=='Payable Voucher' and 'against_voucher' or 'against_invoice', cstr(against_document_no), d.jv_detail_no))

				# re-submit JV
				jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children =1)
				get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel = 0, adv_adj =1)

			elif flt(d.advance_amount) > flt(d.allocated_amount):
				# cancel JV
				jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children=1)
				get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel =1, adv_adj = 1)

				# add extra entries
				self.add_extra_entry(jv_obj, d.journal_voucher, d.jv_detail_no, flt(d.allocated_amount), account_head, doctype, dr_or_cr, against_document_no)

				# re-submit JV
				jv_obj = get_obj('Journal Voucher', d.journal_voucher, with_children =1)
				get_obj(dt='GL Control').make_gl_entries(jv_obj.doc, jv_obj.doclist, cancel = 0, adv_adj = 1)
			else:
				msgprint("Allocation amount cannot be greater than advance amount")
				raise Exception

	# Add extra row in jv detail for unadjusted amount
	#--------------------------------------------------
	def add_extra_entry(self,jv_obj,jv,jv_detail_no, allocate, account_head, doctype, dr_or_cr, against_document_no):
		# get old entry details

		jvd = sql("select %s, cost_center, balance, against_account from `tabJournal Voucher Detail` where name = '%s'" % (dr_or_cr,jv_detail_no))
		advance = jvd and flt(jvd[0][0]) or 0
		balance = flt(advance) - flt(allocate)

		# update old entry
		sql("update `tabJournal Voucher Detail` set %s = '%s', %s = '%s' where name = '%s'" % (dr_or_cr, flt(allocate), doctype == "Payable Voucher" and 'against_voucher' or 'against_invoice',cstr(against_document_no), jv_detail_no))

		# new entry with balance amount
		add = addchild(jv_obj.doc, 'entries', 'Journal Voucher Detail', 1, jv_obj.doclist)
		add.account = account_head
		add.cost_center = cstr(jvd[0][1])
		add.balance = cstr(jvd[0][2])
		add.fields[dr_or_cr] = balance
		add.against_account = cstr(jvd[0][3])
		add.is_advance = 'Yes'
		add.save(1)

	# check if advance entries are still valid
	# ----------------------------------------
	def validate_jv_entry(self, d, account_head, dr_or_cr):
		# 1. check if there is already a voucher reference
		# 2. check if amount is same
		# 3. check if is_advance is 'Yes'
		# 4. check if jv is submitted
		ret = sql("select t2.%s from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 where t1.name = t2.parent and (t2.against_voucher = '' or t2.against_voucher is null) and (t2.against_invoice = '' or t2.against_invoice is null) and t2.account = '%s' and t1.name = '%s' and t2.name = '%s' and t2.is_advance = 'Yes' and t1.docstatus=1 and t2.%s = %s" % ( dr_or_cr, account_head, d.journal_voucher, d.jv_detail_no, dr_or_cr, d.advance_amount))
		if (not ret):
			msgprint("Please click on 'Get Advances Paid' button as the advance entries have been changed.")
			raise Exception
		return

##############################################################################
# Repair Outstanding Amount
##############################################################################
	def repair_voucher_outstanding(self, voucher_obj):
		msg = []

		# Get Balance from GL Entries
		bal = sql("select sum(debit)-sum(credit) from `tabGL Entry` where against_voucher=%s and against_voucher_type=%s", (voucher_obj.doc.name , voucher_obj.doc.doctype))
		bal = bal and flt(bal[0][0]) or 0.0
		if cstr(voucher_obj.doc.doctype) == 'Payable Voucher':
			bal = -bal

		# Check outstanding Amount
		if flt(voucher_obj.doc.outstanding_amount) != flt(bal):
			msgprint('<div style="color: RED"> Difference found in Outstanding Amount of %s : %s (Before : %s; After : %s) </div>' % (voucher_obj.doc.doctype, voucher_obj.doc.name, voucher_obj.doc.outstanding_amount, bal))
			msg.append('<div style="color: RED"> Difference found in Outstanding Amount of %s : %s (Before : %s; After : %s) </div>' % (voucher_obj.doc.doctype, voucher_obj.doc.name, voucher_obj.doc.outstanding_amount, bal))

			# set voucher balance
			#sql("update `tab%s` set outstanding_amount=%s where name='%s'" % (voucher_obj.doc.doctype, bal, voucher_obj.doc.name))
			webnotes.conn.set(voucher_obj.doc, 'outstanding_amount', flt(bal))

		# Send Mail
		if msg:
			email_msg = """ Dear Administrator,

In Account := %s User := %s has Repaired Outstanding Amount For %s : %s and following was found:-

%s

""" % (get_value('Control Panel', None,'account_id'), session['user'], voucher_obj.doc.doctype, voucher_obj.doc.name, '\n'.join(msg))

			sendmail(['support@iwebnotes.com'], subject='Repair Outstanding Amount', parts = [('text/plain', email_msg)])
		# Acknowledge User
		msgprint(cstr(voucher_obj.doc.doctype) + " : " + cstr(voucher_obj.doc.name) + " has been checked" + cstr(msg and " and repaired successfully." or ". No changes Found."))

	def repost_illegal_cancelled(self, after_date='2011-01-01'):
		"""
			Find vouchers that are not cancelled correctly and repost them
		"""
		vl = sql("""
			select voucher_type, voucher_no, account, sum(debit) as sum_debit, sum(credit) as sum_credit
			from `tabGL Entry`
			where is_cancelled='Yes' and creation > %s
			group by voucher_type, voucher_no, account
			""", after_date, as_dict=1)

		ac_list = []
		for v in vl:
			if v['sum_debit'] != 0 or v['sum_credit'] != 0:
				ac_list.append(v['account'])

		fy_list = sql("""select name from `tabFiscal Year`
		where (%s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day))
		or year_start_date > %s
		order by year_start_date ASC""", (after_date, after_date))

		for fy in fy_list:
			fy_obj = get_obj('Fiscal Year', fy[0])
			for a in set(ac_list):
				fy_obj.repost(a)

