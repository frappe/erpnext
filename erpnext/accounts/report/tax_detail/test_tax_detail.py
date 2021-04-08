from __future__ import unicode_literals

import frappe, unittest, datetime, json, os
from frappe.utils import getdate, add_to_date, get_first_day, get_last_day
from .tax_detail import filter_match, save_custom_report

class TestTaxDetail(unittest.TestCase):
	def load_testdocs(self):
		datapath, _ = os.path.splitext(os.path.realpath(__file__))
		with open(datapath + '.json', 'r') as fp:
			self.docs = json.load(fp)

	def load_defcols(self):
		custom_report = frappe.get_doc('Report', 'Tax Detail')
		self.default_columns, _ = custom_report.run_query_report(
			filters={
				'from_date': '2021-03-01',
				'to_date': '2021-03-31',
				'company': '_T',
				'mode': 'run',
				'report_name': 'Tax Detail'
			}, user=frappe.session.user)

	def setUp(self):
		"Add Transactions in 01-03-2021 - 31-03-2021"
		self.load_testdocs()
		now = getdate()
		self.from_date = get_first_day(now)
		self.to_date = get_last_day(now)

		for doc in self.docs:
			try:
				db_doc = frappe.get_doc(doc)
				if 'Invoice' in db_doc.doctype:
					db_doc.due_date = add_to_date(now, days=1)
					db_doc.insert()
					# Create GL Entries:
					db_doc.submit()
				else:
					db_doc.insert()
			except frappe.exceptions.DuplicateEntryError as e:
				pass
				#print(f'Duplicate Entry: {e}')
			except:
				print(f'\nError importing {doc["doctype"]}: {doc["name"]}')
				raise

		self.load_defcols()

	def tearDown(self):
		"Remove the Company and all data"
		from erpnext.setup.doctype.company.delete_company_transactions import delete_company_transactions
		for co in filter(lambda doc: doc['doctype'] == 'Company', self.docs):
			delete_company_transactions(co['name'])
			db_co = frappe.get_doc('Company', co['name'])
			db_co.delete()

	def test_report(self):
		report_name = save_custom_report(
			'Tax Detail',
			'_Test Tax Detail',
			json.dumps({
				'columns': self.default_columns,
				'sections': {
					'Box1':{'Filter0':{'type':'filter','filters':{'4':'VAT on Sales'}}},
					'Box2':{'Filter0':{'type':'filter','filters':{'4':'Acquisition'}}},
					'Box3':{'Box1':{'type':'section'},'Box2':{'type':'section'}},
					'Box4':{'Filter0':{'type':'filter','filters':{'4':'VAT on Purchases'}}},
					'Box5':{'Box3':{'type':'section'},'Box4':{'type':'section'}},
					'Box6':{'Filter0':{'type':'filter','filters':{'3':'!=Tax','4':'Sales'}}},
					'Box7':{'Filter0':{'type':'filter','filters':{'2':'Expense','3':'!=Tax'}}},
					'Box8':{'Filter0':{'type':'filter','filters':{'3':'!=Tax','4':'Sales','12':'EU'}}},
					'Box9':{'Filter0':{'type':'filter','filters':{'2':'Expense','3':'!=Tax','12':'EU'}}}
				},
				'show_detail': 1
			}))
		data = frappe.desk.query_report.run(report_name,
			filters={
				'from_date': self.from_date,
				'to_date': self.to_date,
				'company': '_T',
				'mode': 'run',
				'report_name': report_name
			}, user=frappe.session.user)

		self.assertListEqual(data.get('columns'), self.default_columns)
		expected = (('Box1', 43.25), ('Box2', 0.0), ('Box3', 43.25), ('Box4', -85.28), ('Box5', -42.03),
			('Box6', 825.0), ('Box7', -426.40), ('Box8', 0.0), ('Box9', 0.0))
		exrow = iter(expected)
		for row in data.get('result'):
			if row.get('voucher_no') and not row.get('posting_date'):
				label, value = next(exrow)
				self.assertDictEqual(row, {'voucher_no': label, 'amount': value})
		self.assertListEqual(data.get('report_summary'),
			[{'label': label, 'datatype': 'Currency', 'value': value} for label, value in expected])

	def test_filter_match(self):
		# None - treated as -inf number except range
		self.assertTrue(filter_match(None, '!='))
		self.assertTrue(filter_match(None, '<'))
		self.assertTrue(filter_match(None, '<jjj'))
		self.assertTrue(filter_match(None, '  :  '))
		self.assertTrue(filter_match(None, ':56'))
		self.assertTrue(filter_match(None, ':de'))
		self.assertFalse(filter_match(None, '3.4'))
		self.assertFalse(filter_match(None, '='))
		self.assertFalse(filter_match(None, '=3.4'))
		self.assertFalse(filter_match(None, '>3.4'))
		self.assertFalse(filter_match(None, '   <'))
		self.assertFalse(filter_match(None, 'ew'))
		self.assertFalse(filter_match(None, ' '))
		self.assertFalse(filter_match(None, ' f :'))

		# Numbers
		self.assertTrue(filter_match(3.4, '3.4'))
		self.assertTrue(filter_match(3.4, '.4'))
		self.assertTrue(filter_match(3.4, '3'))
		self.assertTrue(filter_match(-3.4, '< -3'))
		self.assertTrue(filter_match(-3.4, '> -4'))
		self.assertTrue(filter_match(3.4, '= 3.4 '))
		self.assertTrue(filter_match(3.4, '!=4.5'))
		self.assertTrue(filter_match(3.4, ' 3 : 4 '))
		self.assertTrue(filter_match(0.0, '  :  '))
		self.assertFalse(filter_match(3.4, '=4.5'))
		self.assertFalse(filter_match(3.4, ' = 3.4 '))
		self.assertFalse(filter_match(3.4, '!=3.4'))
		self.assertFalse(filter_match(3.4, '>6'))
		self.assertFalse(filter_match(3.4, '<-4.5'))
		self.assertFalse(filter_match(3.4, '4.5'))
		self.assertFalse(filter_match(3.4, '5:9'))

		# Strings
		self.assertTrue(filter_match('ACC-SINV-2021-00001', 'SINV'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', 'sinv'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '-2021'))
		self.assertTrue(filter_match(' ACC-SINV-2021-00001', ' acc'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '=2021'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '!=zz'))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '<   zzz  '))
		self.assertTrue(filter_match('ACC-SINV-2021-00001', '  :  sinv  '))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '  sinv  :'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', ' acc'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '= 2021 '))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '!=sinv'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', ' >'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '>aa'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', ' <'))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '<   '))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', ' ='))
		self.assertFalse(filter_match('ACC-SINV-2021-00001', '='))

		# Date - always match
		self.assertTrue(filter_match(datetime.date(2021, 3, 19), ' kdsjkldfs '))
