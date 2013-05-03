import webnotes
import unittest

class TestSalesInvoice(unittest.TestCase):
	def make(self):
		w = webnotes.bean(webnotes.copy_doclist(test_records[0]))
		w.insert()
		w.submit()
		return w

	def test_outstanding(self):
		w = self.make()
		self.assertEquals(w.doc.outstanding_amount, w.doc.grand_total)
		
	def test_payment(self):
		w = self.make()
		from accounts.doctype.journal_voucher.test_journal_voucher \
			import test_records as jv_test_records
			
		jv = webnotes.bean(webnotes.copy_doclist(jv_test_records[0]))
		jv.doclist[1].against_invoice = w.doc.name
		jv.insert()
		jv.submit()
		
		self.assertEquals(webnotes.conn.get_value("Sales Invoice", w.doc.name, "outstanding_amount"),
			161.8)
	
		jv.cancel()
		self.assertEquals(webnotes.conn.get_value("Sales Invoice", w.doc.name, "outstanding_amount"),
			561.8)
			
	def test_time_log_batch(self):
		tlb = webnotes.bean("Time Log Batch", "_T-Time Log Batch-00001")
		tlb.submit()
		
		si = webnotes.bean(webnotes.copy_doclist(test_records[0]))
		si.doclist[1].time_log_batch = "_T-Time Log Batch-00001"
		si.insert()
		si.submit()
		
		self.assertEquals(webnotes.conn.get_value("Time Log Batch", "_T-Time Log Batch-00001",
		 	"status"), "Billed")

		self.assertEquals(webnotes.conn.get_value("Time Log", "_T-Time Log-00001", "status"), 
			"Billed")

		si.cancel()

		self.assertEquals(webnotes.conn.get_value("Time Log Batch", "_T-Time Log Batch-00001", 
			"status"), "Submitted")

		self.assertEquals(webnotes.conn.get_value("Time Log", "_T-Time Log-00001", "status"), 
			"Batched for Billing")
			
	def test_sales_invoice_gl_entry_without_aii(self):
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		
		si = webnotes.bean(webnotes.copy_doclist(test_records[1]))
		si.insert()
		si.submit()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""", si.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		expected_values = sorted([
			[si.doc.debit_to, 630.0, 0.0],
			[test_records[1][1]["income_account"], 0.0, 500.0],
			[test_records[1][2]["account_head"], 0.0, 80.0],
			[test_records[1][3]["account_head"], 0.0, 50.0],
		])
		
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
			
		# cancel
		si.cancel()
		
		gle_count = webnotes.conn.sql("""select count(name) from `tabGL Entry` 
			where voucher_type='Sales Invoice' and voucher_no=%s 
			and ifnull(is_cancelled, 'No') = 'Yes'
			order by account asc""", si.doc.name)
		
		self.assertEquals(gle_count[0][0], 8)
		
	def test_pos_gl_entry_with_aii(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		old_default_company = webnotes.conn.get_default("company")
		webnotes.conn.set_default("company", "_Test Company")
		
		self._insert_purchase_receipt()
		self._insert_pos_settings()
		
		pos = webnotes.copy_doclist(test_records[1])
		pos[0]["is_pos"] = 1
		pos[0]["update_stock"] = 1
		pos[0]["posting_time"] = "12:05"
		pos[0]["cash_bank_account"] = "_Test Account Bank Account - _TC"
		pos[0]["paid_amount"] = 600.0

		si = webnotes.bean(pos)
		si.insert()
		si.submit()
		
		# check stock ledger entries
		sle = webnotes.conn.sql("""select * from `tabStock Ledger Entry` 
			where voucher_type = 'Sales Invoice' and voucher_no = %s""", 
			si.doc.name, as_dict=1)[0]
		self.assertTrue(sle)
		self.assertEquals([sle.item_code, sle.warehouse, sle.actual_qty], 
			["_Test Item", "_Test Warehouse", -5.0])
		
		# check gl entries
		stock_in_hand_account = webnotes.conn.get_value("Company", "_Test Company", 
			"stock_in_hand_account")
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc, debit asc""", si.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		expected_gl_entries = sorted([
			[si.doc.debit_to, 630.0, 0.0],
			[test_records[1][1]["income_account"], 0.0, 500.0],
			[test_records[1][2]["account_head"], 0.0, 80.0],
			[test_records[1][3]["account_head"], 0.0, 50.0],
			[stock_in_hand_account, 0.0, 375.0],
			[test_records[1][1]["expense_account"], 375.0, 0.0],
			[si.doc.debit_to, 0.0, 600.0],
			["_Test Account Bank Account - _TC", 600.0, 0.0]
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_gl_entries[i][0], gle.account)
			self.assertEquals(expected_gl_entries[i][1], gle.debit)
			self.assertEquals(expected_gl_entries[i][2], gle.credit)
		
		# cancel
		si.cancel()
		gl_count = webnotes.conn.sql("""select count(name)
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			and ifnull(is_cancelled, 'No') = 'Yes' 
			order by account asc, name asc""", si.doc.name)
		
		self.assertEquals(gl_count[0][0], 16)
			
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		webnotes.conn.set_default("company", old_default_company)
		
	def test_sales_invoice_gl_entry_with_aii_no_item_code(self):		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
				
		si_copy = webnotes.copy_doclist(test_records[1])
		si_copy[1]["item_code"] = None
		si = webnotes.bean(si_copy)		
		si.insert()
		si.submit()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""", si.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		expected_values = sorted([
			[si.doc.debit_to, 630.0, 0.0],
			[test_records[1][1]["income_account"], 0.0, 500.0],
			[test_records[1][2]["account_head"], 0.0, 80.0],
			[test_records[1][3]["account_head"], 0.0, 50.0],
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
				
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
	
	def test_sales_invoice_gl_entry_with_aii_non_stock_item(self):		
		webnotes.defaults.set_global_default("auto_inventory_accounting", 1)
		
		si_copy = webnotes.copy_doclist(test_records[1])
		si_copy[1]["item_code"] = "_Test Non Stock Item"
		si = webnotes.bean(si_copy)
		si.insert()
		si.submit()
		
		gl_entries = webnotes.conn.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Sales Invoice' and voucher_no=%s
			order by account asc""", si.doc.name, as_dict=1)
		self.assertTrue(gl_entries)
		
		expected_values = sorted([
			[si.doc.debit_to, 630.0, 0.0],
			[test_records[1][1]["income_account"], 0.0, 500.0],
			[test_records[1][2]["account_head"], 0.0, 80.0],
			[test_records[1][3]["account_head"], 0.0, 50.0],
		])
		for i, gle in enumerate(gl_entries):
			self.assertEquals(expected_values[i][0], gle.account)
			self.assertEquals(expected_values[i][1], gle.debit)
			self.assertEquals(expected_values[i][2], gle.credit)
				
		webnotes.defaults.set_global_default("auto_inventory_accounting", 0)
		
	def _insert_purchase_receipt(self):
		from stock.doctype.purchase_receipt.test_purchase_receipt import test_records \
			as pr_test_records
		pr = webnotes.bean(copy=pr_test_records[0])
		pr.run_method("calculate_taxes_and_totals")
		pr.insert()
		pr.submit()
		
	def _insert_delivery_note(self):
		from stock.doctype.delivery_note.test_delivery_note import test_records \
			as dn_test_records
		dn = webnotes.bean(copy=dn_test_records[0])
		dn.insert()
		dn.submit()
		return dn
		
	def _insert_pos_settings(self):
		from accounts.doctype.pos_setting.test_pos_setting \
			import test_records as pos_setting_test_records
		webnotes.conn.sql("""delete from `tabPOS Setting`""")
		
		ps = webnotes.bean(copy=pos_setting_test_records[0])
		ps.insert()
		
	def test_sales_invoice_with_advance(self):
		from accounts.doctype.journal_voucher.test_journal_voucher \
			import test_records as jv_test_records
			
		jv = webnotes.bean(copy=jv_test_records[0])
		jv.insert()
		jv.submit()
		
		si = webnotes.bean(copy=test_records[0])
		si.doclist.append({
			"doctype": "Sales Invoice Advance",
			"parentfield": "advance_adjustment_details",
			"journal_voucher": jv.doc.name,
			"jv_detail_no": jv.doclist[1].name,
			"advance_amount": 400,
			"allocated_amount": 300,
			"remarks": jv.doc.remark
		})
		si.insert()
		si.submit()
		si.load_from_db()
		
		self.assertTrue(webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_invoice=%s""", si.doc.name))
		
		self.assertTrue(webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_invoice=%s and credit=300""", si.doc.name))
			
		self.assertEqual(si.doc.outstanding_amount, 261.8)
		
		si.cancel()
		
		self.assertTrue(not webnotes.conn.sql("""select name from `tabJournal Voucher Detail`
			where against_invoice=%s""", si.doc.name))
			
	def test_recurring_invoice(self):
		from webnotes.utils import now_datetime, get_first_day, get_last_day, add_to_date
		today = now_datetime().date()
		
		base_si = webnotes.bean(copy=test_records[0])
		base_si.doc.fields.update({
			"convert_into_recurring_invoice": 1,
			"recurring_type": "Monthly",
			"notification_email_address": "test@example.com, test1@example.com, test2@example.com",
			"repeat_on_day_of_month": today.day,
			"posting_date": today,
			"invoice_period_from_date": get_first_day(today),
			"invoice_period_to_date": get_last_day(today)
		})
		
		# monthly
		si1 = webnotes.bean(copy=base_si.doclist)
		si1.insert()
		si1.submit()
		self._test_recurring_invoice(si1, True)
		
		# monthly without a first and last day period
		si2 = webnotes.bean(copy=base_si.doclist)
		si2.doc.fields.update({
			"invoice_period_from_date": today,
			"invoice_period_to_date": add_to_date(today, days=30)
		})
		si2.insert()
		si2.submit()
		self._test_recurring_invoice(si2, False)
		
		# quarterly
		si3 = webnotes.bean(copy=base_si.doclist)
		si3.doc.fields.update({
			"recurring_type": "Quarterly",
			"invoice_period_from_date": get_first_day(today),
			"invoice_period_to_date": get_last_day(add_to_date(today, months=3))
		})
		si3.insert()
		si3.submit()
		self._test_recurring_invoice(si3, True)
		
		# quarterly without a first and last day period
		si4 = webnotes.bean(copy=base_si.doclist)
		si4.doc.fields.update({
			"recurring_type": "Quarterly",
			"invoice_period_from_date": today,
			"invoice_period_to_date": add_to_date(today, months=3)
		})
		si4.insert()
		si4.submit()
		self._test_recurring_invoice(si4, False)
		
		# yearly
		si5 = webnotes.bean(copy=base_si.doclist)
		si5.doc.fields.update({
			"recurring_type": "Yearly",
			"invoice_period_from_date": get_first_day(today),
			"invoice_period_to_date": get_last_day(add_to_date(today, years=1))
		})
		si5.insert()
		si5.submit()
		self._test_recurring_invoice(si5, True)
		
		# yearly without a first and last day period
		si6 = webnotes.bean(copy=base_si.doclist)
		si6.doc.fields.update({
			"recurring_type": "Yearly",
			"invoice_period_from_date": today,
			"invoice_period_to_date": add_to_date(today, years=1)
		})
		si6.insert()
		si6.submit()
		self._test_recurring_invoice(si6, False)
		
		# change posting date but keep recuring day to be today
		si7 = webnotes.bean(copy=base_si.doclist)
		si7.doc.fields.update({
			"posting_date": add_to_date(today, days=-1)
		})
		si7.insert()
		si7.submit()
		
		# setting so that _test function works
		si7.doc.posting_date = today
		self._test_recurring_invoice(si7, True)

	def _test_recurring_invoice(self, base_si, first_and_last_day):
		from webnotes.utils import add_months, get_last_day, getdate
		from accounts.doctype.sales_invoice.sales_invoice import manage_recurring_invoices
		
		no_of_months = ({"Monthly": 1, "Quarterly": 3, "Yearly": 12})[base_si.doc.recurring_type]
		
		def _test(i):
			self.assertEquals(i+1, webnotes.conn.sql("""select count(*) from `tabSales Invoice`
				where recurring_id=%s and docstatus=1""", base_si.doc.recurring_id)[0][0])
				
			next_date = add_months(base_si.doc.posting_date, no_of_months)
			
			manage_recurring_invoices(next_date=next_date, commit=False)
			
			recurred_invoices = webnotes.conn.sql("""select name from `tabSales Invoice`
				where recurring_id=%s and docstatus=1 order by name desc""",
				base_si.doc.recurring_id)
			
			self.assertEquals(i+2, len(recurred_invoices))
			
			new_si = webnotes.bean("Sales Invoice", recurred_invoices[0][0])
			
			for fieldname in ["convert_into_recurring_invoice", "recurring_type",
				"repeat_on_day_of_month", "notification_email_address"]:
					self.assertEquals(base_si.doc.fields.get(fieldname),
						new_si.doc.fields.get(fieldname))

			self.assertEquals(new_si.doc.posting_date, unicode(next_date))
			
			self.assertEquals(new_si.doc.invoice_period_from_date,
				unicode(add_months(base_si.doc.invoice_period_from_date, no_of_months)))
			
			if first_and_last_day:
				self.assertEquals(new_si.doc.invoice_period_to_date, 
					unicode(get_last_day(add_months(base_si.doc.invoice_period_to_date,
						no_of_months))))
			else:
				self.assertEquals(new_si.doc.invoice_period_to_date, 
					unicode(add_months(base_si.doc.invoice_period_to_date, no_of_months)))
					
			self.assertEquals(getdate(new_si.doc.posting_date).day, 
				base_si.doc.repeat_on_day_of_month)
			
			return new_si
		
		# if yearly, test 3 repetitions, else test 13 repetitions
		count = no_of_months == 12 and 3 or 13
		for i in xrange(count):
			base_si = _test(i)
		
test_dependencies = ["Journal Voucher", "POS Setting", "Contact", "Address"]

test_records = [
	[
		{
			"naming_series": "_T-Sales Invoice-",
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"debit_to": "_Test Customer - _TC",
			"customer": "_Test Customer",
			"customer_name": "_Test Customer",
			"doctype": "Sales Invoice", 
			"due_date": "2013-01-23", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"grand_total": 561.8, 
			"grand_total_export": 561.8, 
			"net_total": 500.0, 
			"plc_conversion_rate": 1.0, 
			"posting_date": "2013-01-23", 
			"price_list_currency": "INR", 
			"price_list_name": "_Test Price List", 
			"territory": "_Test Territory"
		}, 
		{
			"amount": 500.0, 
			"basic_rate": 500.0, 
			"description": "138-CMS Shoe", 
			"doctype": "Sales Invoice Item", 
			"export_amount": 500.0, 
			"export_rate": 500.0, 
			"income_account": "Sales - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"item_name": "138-CMS Shoe", 
			"parentfield": "entries",
			"qty": 1.0
		}, 
		{
			"account_head": "_Test Account VAT - _TC", 
			"charge_type": "On Net Total", 
			"description": "VAT", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"tax_amount": 30.0,
		}, 
		{
			"account_head": "_Test Account Service Tax - _TC", 
			"charge_type": "On Net Total", 
			"description": "Service Tax", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"tax_amount": 31.8,
		},
		{
			"parentfield": "sales_team",
			"doctype": "Sales Team",
			"sales_person": "_Test Sales Person 1",
			"allocated_percentage": 65.5,
		},
		{
			"parentfield": "sales_team",
			"doctype": "Sales Team",
			"sales_person": "_Test Sales Person 2",
			"allocated_percentage": 34.5,
		},
	],
	[
		{
			"naming_series": "_T-Sales Invoice-",
			"company": "_Test Company", 
			"conversion_rate": 1.0, 
			"currency": "INR", 
			"debit_to": "_Test Customer - _TC",
			"customer": "_Test Customer",
			"customer_name": "_Test Customer",
			"doctype": "Sales Invoice", 
			"due_date": "2013-01-23", 
			"fiscal_year": "_Test Fiscal Year 2013", 
			"grand_total": 630.0, 
			"grand_total_export": 630.0, 
			"net_total": 500.0, 
			"plc_conversion_rate": 1.0, 
			"posting_date": "2013-03-07", 
			"price_list_currency": "INR", 
			"price_list_name": "_Test Price List", 
			"territory": "_Test Territory"
		}, 
		{
			"item_code": "_Test Item",
			"item_name": "_Test Item", 
			"description": "_Test Item", 
			"doctype": "Sales Invoice Item", 
			"parentfield": "entries",
			"qty": 5.0,
			"basic_rate": 500.0,
			"amount": 500.0, 
			"export_rate": 500.0, 
			"export_amount": 500.0, 
			"income_account": "Sales - _TC",
			"expense_account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
		}, 
		{
			"account_head": "_Test Account VAT - _TC", 
			"charge_type": "On Net Total", 
			"description": "VAT", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"tax_amount": 80.0,
		}, 
		{
			"account_head": "_Test Account Service Tax - _TC", 
			"charge_type": "On Net Total", 
			"description": "Service Tax", 
			"doctype": "Sales Taxes and Charges", 
			"parentfield": "other_charges",
			"tax_amount": 50.0,
		}
	],
]