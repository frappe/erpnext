from __future__ import unicode_literals
import frappe, unittest
from erpnext.hr.doctype.payroll_entry.test_payroll_entry import make_payroll_entry
from frappe.utils import add_to_date, get_datetime, now
from erpnext.hr.report.bank_remittance.bank_remittance import execute

class TestBankRemittance(unittest.TestCase):

	def setUp(self):
		frappe.db.sql("DELETE FROM `tabEmployee` WHERE `first_name` IN ('Report_test_Employee_1','Report_test_Employee_2');")
		frappe.db.sql("DELETE FROM `tabSalary Structure` WHERE `name` = 'Report_salary_structure';")
		frappe.db.sql("DELETE FROM `tabSalary Structure Assignment` WHERE `salary_structure` = 'Report_salary_structure';")
		frappe.db.sql("DELETE FROM `tabBank` WHERE `bank_name` = 'Remittance_Bank';")
		frappe.db.sql("DELETE FROM `tabBank Account` WHERE `account_name` = 'Test_bank_account_for_remittance';")
		frappe.db.sql("DELETE FROM `tabSalary Component` WHERE `salary_component` = '_Test Basic';")

	def test_for_get_salary_transfer_transaction_in_report(self):
		emp_1 = get_employee("Report_test_Employee_1")
		emp_2 = get_employee("Report_test_Employee_2")
		salary_structure = get_salary_structure()
		emp_1_assignment = get_salary_structure_assignment(emp_1.name, salary_structure.name)
		emp_2_assignment = get_salary_structure_assignment(emp_2.name, salary_structure.name)
		start = get_datetime(now()).replace(day=1)

		end = add_to_date(start, months=1, days=-1 )

		bank = frappe.new_doc("Bank")
		bank.bank_name = "Remittance_Bank"
		bank.save()

		create_bank_account(bank.name)

		payroll_entry = make_payroll_entry(start_date = start , end_date=end, company="_Test Company", payment_account="_Test Bank - _TC")
		submit_salary_slips(payroll_entry.name)

		cols, rows = execute(filters=frappe._dict({'company': '_Test Company' }))

		self.assertEquals(len(rows), 2)

		employee_map = {}
		for row in rows:
			employee_map[row['employee_name']] = row

		name_str = emp_1.name+": "+"Report_test_Employee_1"

		self.assertEquals(employee_map[name_str]['amount'], 1000)
		self.assertEquals(employee_map[name_str]['bank_code'], 'Test_ifsc_code')
		self.assertEquals(employee_map[name_str]['bank_name'], 'HDFC')
		self.assertEquals(employee_map[name_str]['debit_account'], '0987654321')
		self.assertEquals(employee_map[name_str]['employee_account_no'], '123456789')
		self.assertEquals(employee_map[name_str]['payroll_no'], payroll_entry.name)

def get_employee(emp_name):
	emp = frappe.new_doc("Employee")
	emp.first_name = emp_name
	emp.gender = "Male"
	emp.date_of_birth = get_datetime("03-08-1997")
	emp.date_of_joining = now()
	emp.salary_mode = "Bank"
	emp.bank_name ="HDFC"
	emp.bank_ac_no = "123456789"
	emp.ifsc_code = "Test_ifsc_code"
	emp.company = "_Test Company"

	emp.insert()
	return emp

def get_salary_structure():
	salary_structure = frappe.new_doc("Salary Structure")
	salary_structure.name = "Report_salary_structure"
	salary_structure.company = "_Test Company"
	salary_structure.payroll_frequency = "Monthly"


	component = frappe.get_doc({
		"doctype": "Salary Component",
		"salary_component": "_Test Basic",
		"type": "Earning",
		"is_tax_applicable": 0,
		"depends_on_payment_days": 0,
		"is_payable": 1
	})

	component.insert()

	salary_structure.append("earnings", {
		"salary_component" : component.name,
		"amount": 1000
		})

	salary_structure.insert()
	salary_structure.submit()
	return salary_structure

def get_salary_structure_assignment(emp_name, salary_structure):
	assignment = frappe.new_doc("Salary Structure Assignment")
	assignment.employee = emp_name
	assignment.salary_structure = salary_structure
	assignment.from_date = now()
	assignment.company = "_Test Company"

	assignment.insert()
	assignment.submit()
	return assignment

def create_bank_account(bank):
	bank_account = frappe.new_doc("Bank Account")
	bank_account.account_name = "Test_bank_account_for_remittance"
	bank_account.account = "_Test Bank - _TC"
	bank_account.bank =  bank
	bank_account.is_company_account = 1
	bank_account.is_default = 1
	bank_account.bank_account_no = "0987654321"
	bank_account.company = "_Test Company"
	bank_account.save()

def submit_salary_slips(payroll_entry_name):
	slips = frappe.get_all("Salary Slip", filters={'payroll_entry': payroll_entry_name})

	for slip in slips:
		frappe.get_doc("Salary Slip", slip.name).submit()