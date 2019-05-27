from __future__ import unicode_literals
import frappe, unittest

class TestBankRemittance(unittest.TestCase):

    def setUp(self):
        frappe.db.sql("DELETE FROM `tabEmployee` WHERE `first_name` IN ('Report_test_Employee_1','Report_test_Employee_2');")
        frappe.db.sql("DELETE FROM `tabSalary Structure` WHERE `name` = 'Report_salary_structure';")
        frappe.db.sql("DELETE FROM `tabSalary Structure Assignment` WHERE `salary_structure` = 'Report_salary_structure';")



    def test_for_get_salary_transfer_transaction_in_report(self):
        emp_1 = get_employee("Report_test_Employee_1")
        emp_2 = get_employee("Report_test_Employee_2")
        print(emp_1.name, emp_2.name)
        salary_structure = get_salary_structure()
        print(salary_structure.name)
        emp_1_assignment = get_salary_structure_assignment(emp_1.name, salary_structure.name)
        emp_2_assignment = get_salary_structure_assignment(emp_2.name, salary_structure.name)
        print(emp_1_assignment.name, emp_2_assignment.name)


def get_employee(emp_name):
    emp = frappe.new_doc("Employee")
    emp.first_name = emp_name
    emp.gender = "Male"
    emp.date_of_birth = frappe.utils.get_datetime("03-08-1997")
    emp.date_of_joining = frappe.utils.now()
    emp.salary_mode = "Bank"
    emp.bank_name ="HDFC"
    emp.bank_ac_no = "123456789"
    emp.ifsc_code = "Test_ifsc_code"

    emp.insert()
    return emp

def get_salary_structure():
    salary_structure = frappe.new_doc("Salary Structure")
    salary_structure.name = "Report_salary_structure"
    salary_structure.company = "_Test Company"
    salary_structure.payroll_frequency = "Monthly"

    salary_structure.append("earnings", {
        "salary_component" : "Basic",
        "amount": 1000
        })

    salary_structure.insert()
    return salary_structure

def get_salary_structure_assignment(emp_name, salary_structure):
    assignment = frappe.new_doc("Salary Structure Assignment")
    assignment.employee = emp_name
    assignment.salary_structure = salary_structure
    assignment.from_date = frappe.utils.now()

    assignment.insert()
    return assignment

