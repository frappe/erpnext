import unittest
import webnotes
from webnotes.model.code import get_obj

class TestScheduleGeneartion(unittest.TestCase):
	def setUp(self):
		webnotes.conn.begin()
		# create a mock loan
		self.loan = get_obj('Loan', 'LOAN00001')
		
	def test_generation(self):
		"test the genaration of loan installments"
		self.loan.generate()
		self.assertEqual(self.loan.get_installment_total(), self.loan.doc.loan_amount)
		
	def tearDown(self):
		webnotes.conn.rollback()
