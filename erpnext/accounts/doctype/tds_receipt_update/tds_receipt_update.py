# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, today, get_datetime
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class TDSReceiptUpdate(Document):
	def validate(self):
		self.calculate_total()
		self.validate_filters()

	def on_update(self):
		self.check_duplicate_entries()

	def on_submit(self):
		self.make_tds_receipt_entries()

	def on_cancel(self):
		frappe.db.sql("delete from `tabTDS Receipt Entry` where tds_receipt_update = '{}'".format(self.name))

	def check_duplicate_entries(self):
		if self.purpose in ["Employee Salary","PBVA","Bonus"]:
			filters = {"purpose": self.purpose, "fiscal_year": self.fiscal_year}
			if self.purpose == "Employee Salary":
				filters.update({"month": self.month})

			for t in frappe.db.get_all("TDS Receipt Entry", filters, "tds_receipt_update"):
				frappe.throw(_("Receipt details for <b>{}</b> already updated via {}")\
					.format(self.purpose, frappe.get_desk_link("TDS Receipt Update", t.tds_receipt_update)))
		else:
			for t in frappe.db.sql("""select t1.tds_receipt_update, t1.invoice_type, t1.invoice_no 
					from `tabTDS Receipt Entry` t1
					where exists(select 1
						from `tabTDS Remittance Item` t2
						where t2.parent = "{parent}"
						and t2.invoice_type = t1.invoice_type
						and t2.invoice_no = t1.invoice_no)
				""".format(parent=self.name), as_dict=True):
				frappe.throw(_("Receipt details for {} already updated via {}")\
					.format(frappe.get_desk_link(t.invoice_type, t.invoice_no), frappe.get_desk_link("TDS Receipt Update", t.tds_receipt_update)))

	def calculate_total(self):
		total_bill_amount = total_tds_amount = 0
		for a in self.items:
			total_bill_amount 	+= flt(a.bill_amount)
			total_tds_amount 	+= flt(a.tds_amount)
		self.total_bill_amount 	= total_bill_amount
		self.total_tax_amount 	= total_tds_amount

	def get_entries(self):
		entries = []
		if self.purpose in ["Employee Salary","PBVA","Bonus"]:
			name = make_autoname('TDSRE.YYYY.MM.#######')
			entries.append((name, str(today()), self.branch, self.cost_center, 
				self.purpose, self.fiscal_year, self.month or "", self.pbva or "" if self.purpose == "PBVA" else "", "", 
				"", "", "", 
				self.tds_receipt_date, self.tds_receipt_number, self.cheque_no, self.cheque_date,
				self.name, "", 0, 0, frappe.session.user, str(get_datetime()), str(get_datetime()), frappe.session.user))
		else:
			for d in self.items:
				name = make_autoname('TDSRE.YYYY.MM.#######')
				bill_no = None
				if d.invoice_type == "Leave Encashment":
					employee, employee_name = frappe.db.get_value("Leave Encashment", d.invoice_no, ["employee","employee_name"])
					bill_no = str(employee_name + "(" + d.invoice_no + ")")
				else:
					bill_no = d.invoice_no
				if d.tds_remittance == None:
					d.tds_remittance = ''
				entries.append((name, d.posting_date, self.branch, self.cost_center,
					self.purpose, self.fiscal_year or "", self.month or "", "", self.region or "",
					d.invoice_type, d.invoice_no, bill_no, 
					self.tds_receipt_date, self.tds_receipt_number, self.cheque_no, self.cheque_date, 
					self.name, d.tds_remittance, 0, 0, frappe.session.user, str(get_datetime()), str(get_datetime()), frappe.session.user))
				# frappe.throw(str(entries))
		return entries

	def make_tds_receipt_entries(self):
		entries = self.get_entries()
		if len(entries):
			entries = ', '.join(map(str, entries))
			query = """INSERT INTO `tabTDS Receipt Entry`(name, posting_date, branch, cost_center, 
				purpose, fiscal_year, month, pbva, region,  
				invoice_type, invoice_no, bill_no,
				receipt_date, receipt_number, cheque_no, cheque_date, 
				tds_receipt_update, tds_remittance, idx, docstatus, owner, creation, modified, modified_by)
				VALUES {}""".format(entries)
			frappe.db.sql("""INSERT INTO `tabTDS Receipt Entry`(name, posting_date, branch, cost_center, 
				purpose, fiscal_year, month, pbva, region,  
				invoice_type, invoice_no, bill_no, 
				receipt_date, receipt_number, cheque_no, cheque_date, 
				tds_receipt_update, tds_remittance, idx, docstatus, owner, creation, modified, modified_by)
				VALUES {}""".format(entries))

	def validate_filters(self):
		if self.purpose in ("Employee Salary", "PBVA", "Bonus"):
			if not self.fiscal_year:
				frappe.throw("<b>Fiscal Year</b> is mandatory")
			elif self.purpose == "Employee Salary" and not self.month:
				frappe.throw("<b>Month</b> is mandatory")

	@frappe.whitelist()
	def get_invoices(self):
		cond = accounts_cond = "" 
		total_bill_amount = total_tds_amount = 0
		entries = []
		self.set('items', [])

		accounts = [i.account for i in frappe.db.get_all("Tax Withholding Account", \
			{"parent": self.tax_withholding_category}, "account")]

		if not len(accounts):
			return total_tds_amount, total_bill_amount
		elif len(accounts) == 1:
			accounts_cond = 'and t1.tax_account = "{}"'.format(accounts[0])
		else:
			accounts_cond = 'and t1.tax_account in ({})'.format('"' + '","'.join(accounts) + '"')

		if self.purpose in ["Leave Encashment","Other Invoice","Overtime"]:
			if self.purpose == 'Leave Encashment':
				query = """
					SELECT 
						"Leave Encashment" as invoice_type, 
						name as invoice_no, 
						encashment_date as posting_date, 
						encashment_amount as bill_amount,
						cost_center, 
						encashment_tax as tds_amount, 
						employee as party,
						'Employee' as party_type,
						employee_name as party_name
					FROM `tabLeave Encashment` AS t 
						WHERE t.docstatus = 1 
						AND t.encashment_date BETWEEN '{0}' AND '{1}' 
						AND t.encashment_tax > 0 
						# {2} 
						AND NOT EXISTS (SELECT 1 
					FROM `tabTDS Receipt Entry` AS b 
						WHERE b.invoice_no = t.name)
						""".format(self.from_date, self.to_date, cond)
				query += """
					UNION SELECT 
						"Employee Benefit Claim" as invoice_type, 
						t.name as invoice_no, 
						t.posting_date, 
						t1.amount as bill_amount,
						t.cost_center as cost_center, 
						t1.tax_amount as tds_amount, 
						t.employee as party, 
						'Employee' as party_type,
						t.employee_name as party_name
					FROM `tabEmployee Benefit Claim` AS t, `tabSeparation Item` t1 
						WHERE t.docstatus = 1 
						AND t1.parent = t.name
						AND t.posting_date BETWEEN '{0}' 
						AND '{1}'
						AND t1.tax_amount > 0 {2}
						AND NOT EXISTS (SELECT 1 
					FROM `tabTDS Receipt Entry` AS b 
						WHERE b.invoice_no = t.name)
						""".format(self.from_date, self.to_date, cond)
				entries = frappe.db.sql(query,as_dict=1)
			elif self.purpose == 'Overtime':
				pass
				'''
				query = """select 
							"Overtime Application" as invoice_type, 
								name as invoice_no, 
								posting_date as posting_date, 
								total_amount as bill_amount, 
								overtime_tax as tds_amount, 
								employee as party, 
								'Employee' as party_type
							FROM `tabOvertime Application` AS t 
								WHERE t.docstatus = 1 
							 	AND t.posting_date BETWEEN '{0}' AND '{1}' 
								AND t.overtime_tax > 0 {2}
								AND NOT EXISTS (SELECT 1 FROM `tabRRCO Receipt Entries` AS b 
								WHERE b.purchase_invoice = t.name)
								""".format(self.from_date, self.to_date, cond)
				'''
			else:
				entries = frappe.db.sql("""SELECT posting_date, party_type, party, invoice_type, invoice_no, bill_amount, 
						tax_account, tds_amount, party_name, tpn, cost_center, business_activity, parent as tds_remittance
					FROM `tabTDS Remittance Item` t1
					WHERE t1.posting_date BETWEEN '{from_date}' AND '{to_date}'
					AND t1.docstatus = 1
					{accounts_cond}
					AND t1.parenttype = 'TDS Remittance'
					AND NOT EXISTS(SELECT 1
						FROM `tabTDS Receipt Entry` t2
						WHERE t2.invoice_no = t1.invoice_no)
					AND NOT EXISTS(SELECT 1
						FROM `tabTDS Remittance Item` t3
						WHERE t3.invoice_no = t1.invoice_no
						AND t3.parenttype = 'TDS Receipt Update'
						AND t3.parent != "{name}"
						AND t3.docstatus != 2)
				""".format(name = self.name, accounts_cond = accounts_cond, \
					from_date = self.from_date, to_date = self.to_date),as_dict=True)

			if not len(entries):
				frappe.msgprint(_("No Records Found"))

			for d in entries:
				row = self.append('items', {})
				if self.purpose == "Leave Encashment":
					d.tpn = frappe.db.get_value("Employee", d.party, "tpn_number")
				d.bill_amount = flt(d.bill_amount, 2)
				d.tds_amount = flt(d.tds_amount, 2)
				row.update(d)
				total_bill_amount 	+= flt(d.bill_amount)
				total_tds_amount 	+= flt(d.tds_amount)

		return total_bill_amount, total_tds_amount

@frappe.whitelist()
def apply_pbva_filter(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql('''
		SELECT name
		FROM `tabPBVA` a
		WHERE docstatus = 1
		AND NOT EXISTS(select 1 from `tabRRCO Receipt Entry` where pbva = a.name)
		AND	(`{key}` LIKE %(txt)s OR name LIKE %(txt)s)
		LIMIT %(start)s, %(page_len)s
	'''.format(key=searchfield),{
		'txt': '%' + txt + '%',
		'start': start, 'page_len': page_len
	})

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles or "Accounts User" in user_roles: 
		return

	return """(
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabTDS Receipt Update`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabTDS Receipt Update`.branch)
	)""".format(user=user)