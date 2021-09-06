# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
import frappe
import unittest
from datetime import date
from dateutil.relativedelta import relativedelta

class TestAppraisal(unittest.TestCase):

	@classmethod
	def setUpClass(cls) -> None:
		create_company()
		create_employee()
		create_appraisal_template()

	def test_appraisal_submission(self):
		doc = frappe.new_doc('Appraisal')
		doc.appraisal_template = 'Test Manager'
		doc.start_date = date.today()
		doc.end_date  = date.today() + relativedelta(days=1)
		doc.employee = get_employee('Test_Employee', 'Test Company')
		doc.company = 'Test Company'
		doc.new_designation = "Project Manager"

		doc.append('kra_assessment', {
			'kra': 'KRA 1',
			'kpi': 'KPI 1',
			'per_weightage': 50,
			'mentor_score': 4,
			'self_score': 5
		})

		doc.append('kra_assessment', {
			'kra': 'KRA 2',
			'kpi': 'KPI 2',
			'per_weightage': 50,
			'mentor_score': 4,
			'self_score': 5
		})

		doc.append('behavioural_assessment', {
			'behavioral_parameter': 'Test Behaviour',
			'description': 'Test',
			'mentors_score': 4,
			'self_score': 5

		})

		doc.append('self_improvement_areas', {
			'skill': 'Test Skill',
			'current_score': 4,
			'target_score': 5,
			'achieved_score': 4
		})

		doc.save()
	
	def test_verify_submission(self):
		doc = frappe.db.get_list('Appraisal',
		filters={'employee': get_employee('Test_Employee', 'Test Company')},
		fields=['*'])

		self.assertEqual(doc[0]['overall_self_score'],5.0)
		self.assertEqual(doc[0]['overall_score'],4.0)

def create_company():
	doc = frappe.db.exists('Company', 'Test Company')
	if not doc:
		doc = frappe.new_doc('Company')
		doc.company_name = 'Test Company'
		doc.abbr = 'TCO'
		doc.default_currency = 'INR'
		doc.insert()

def create_employee():
	doc = frappe.db.exists({
			'doctype': 'Employee',
			'first_name': 'Test_Employee'
		})
	if not doc:
		doc = frappe.new_doc('Employee')
		doc.company = 'Test Company'
		doc.first_name = 'Test_Employee'
		doc.date_of_birth = date(1997, 9, 15)
		doc.date_of_joining = date(2021, 9, 30)
		doc.gender = 'Male'
		doc.insert()

def create_appraisal_template():
	doc = frappe.db.exists({
		'doctype': 'Appraisal Template',
		'appraisal_template_title': 'Test Manager'
	})

	if not doc:
		doc = frappe.new_doc('Appraisal Template')
		doc.appraisal_template_title = 'Test Manager'
		doc.description = 'Test'
		doc.append('kra_assessment', {
			'kra': 'KRA 1',
			'kpi': 'KPI 1',
			'per_weightage': 50
		})

		doc.append('kra_assessment', {
			'kra': 'KRA 2',
			'kpi': 'KPI 2',
			'per_weightage': 50
		})

		doc.append('behavioural_assessment', {
			'behavioral_parameter': 'Test Behaviour',
			'description': 'Test'
		})

		doc.append('self_improvement_areas', {
			'skill': 'Test Skill'
		})
		doc.insert()

def get_employee(employee_name, employee_company):
	name = frappe.db.get_value('Employee',{'company':employee_company, 'employee_name': employee_name},['name'])
	return name