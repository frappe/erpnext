$.extend(frappe.test_data, {
	'Academic Year': {
		'2016-17': [
			{academic_year_name: '2016-17'},
			{year_start_date: '2016-07-20'},
			{year_end_date: '2017-06-20'}
		]
	},
	'Academic Term': {
		'2016-17 (Semester 1)': [
			{academic_year: '2016-17'},
			{term_name: 'Semester 1'},
			{term_start_date: '2016-07-20'},
			{term_end_date: '2017-06-20'}
		]
	},
	'Department': {
		'Teaching': [
			{department_name: 'Teaching'}
		]
	},
	'Assessment Criteria Group': {
		'Scholarship': [
			{assessment_criteria_group: 'Scholarship'}
		]
	},
	'Assessment Criteria': {
		'Pass': [
			{assessment_criteria: 'Pass'},
			{assessment_criteria_group: 'Scholarship'}
		]
	},
	'Grading Scale': {
		'GTU': [
			{grading_scale_name: 'GTU'},
			{description: 'The score will be set according to 10 based system.'},
			{intervals: [
				[
					{grade_code: 'AA'},
					{threshold: '90'},
					{grade_description: 'Distinction'}
				],
				[
					{grade_code: 'FF'},
					{threshold: '0'},
					{grade_description: 'Fail'}
				]
			]}
		]
	},
	'Course': {
		'Maths': [
			{course_name: 'Maths'},
			{course_code: '007'},
			{department: 'Teaching'},
			{course_abbreviation: 'Math'},
			{course_intro: 'Testing Intro'},
			{default_grading_scale: 'GTU'},
			{assessment_criteria: [
				[
					{assessment_criteria: 'Pass'},
					{weightage: 100}
				]
			]}
		]
	},
	'Student Category': {
		'Scholarship': [
			{category: 'Scholarship'}
		]
	},
	"Program": {
		"Standard Test": [
			{program_name: 'Standard Test'},
			{program_code: 'Standard Test'},
			{department: 'Teaching'},
			{program_abbreviation: 'Standard Test'}
		]
	},
	"Student Admission": {
		"Test Admission": [
			{academic_year: '2016-17'},
			{admission_start_date: '2016-04-20'},
			{admission_end_date: '2016-05-31'},
			{title: '2016-17 Admissions'},
			{program: 'Standard Test'},
			{application_fee: 1000},
			{naming_series_for_student_applicant: 'AP'},
			{introduction: 'Test intro'},
			{eligibility: 'Test eligibility'}
		]
	},
	"Guardian": {
		"Test Guradian": [
			{guardian_name: 'Test Guardian'},
			{email_address: 'guardian@testmail.com'},
			{mobile_number: 9898980000},
			{alternate_number: 8989890000},
			{date_of_birth: '1982-07-22'},
			{education: 'Testing'},
			{occupation: 'Testing'},
			{designation: 'Testing'},
			{work_address: 'Testing address'}
		]
	},
	"Customer": {
		"Test Customer 1": [
			{customer_name: "Test Customer 1"}
		],
		"Test Customer 2": [
			{customer_name: "Test Customer 2"}
		],
		"Test Customer 3": [
			{customer_name: "Test Customer 3"}
		],
	},
	"Item": {
		"Test Product 1": [
			{item_code: "Test Product 1"},
			{item_group: "Products"},
			{is_stock_item: 1},
			{standard_rate: 100},
			{opening_stock: 100}
		],
		"Test Product 2": [
			{item_code: "Test Product 2"},
			{item_group: "Products"},
			{is_stock_item: 1},
			{standard_rate: 150},
			{opening_stock: 200}
		],
		"Test Product 3": [
			{item_code: "Test Product 3"},
			{item_group: "Products"},
			{is_stock_item: 1},
			{standard_rate: 250},
			{opening_stock: 100}
		],
		"Test Service 1": [
			{item_code: "Test Service 1"},
			{item_group: "Services"},
			{is_stock_item: 0},
			{standard_rate: 200}
		],
		"Test Service 2": [
			{item_code: "Test Service 2"},
			{item_group: "Services"},
			{is_stock_item: 0},
			{standard_rate: 300}
		]
	},
	"Lead": {
		"LEAD-00001": [
			{lead_name: "Test Lead 1"}
		],
		"LEAD-00002": [
			{lead_name: "Test Lead 2"}
		],
		"LEAD-00003": [
			{lead_name: "Test Lead 3"}
		]
	},
	"Address": {
		"Test1-Billing": [
			{address_title:"Test1"},
			{address_type: "Billing"},
			{address_line1: "Billing Street 1"},
			{city: "Billing City 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Test1-Shipping": [
			{address_title:"Test1"},
			{address_type: "Shipping"},
			{address_line1: "Shipping Street 1"},
			{city: "Shipping City 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Test1-Warehouse": [
			{address_title:"Test1"},
			{address_type: "Warehouse"},
			{address_line1: "Warehouse Street 1"},
			{city: "Warehouse City 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Test2-Billing": [
			{address_title:"Test2"},
			{address_type: "Billing"},
			{address_line1: "Billing Street 2"},
			{city: "Billing City 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		],
		"Test2-Shipping": [
			{address_title:"Test2"},
			{address_type: "Shipping"},
			{address_line1: "Shipping Street 2"},
			{city: "Shipping City 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		],
		"Test2-Warehouse": [
			{address_title:"Test2"},
			{address_type: "Warehouse"},
			{address_line1: "Warehouse Street 2"},
			{city: "Warehouse City 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		]
	},
	"Contact": {
		"Contact 1-Test Customer 1": [
			{first_name: "Contact 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Contact 2-Test Customer 1": [
			{first_name: "Contact 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 1"}
				]
			]}
		],
		"Contact 1-Test Customer 2": [
			{first_name: "Contact 1"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		],
		"Contact 2-Test Customer 2": [
			{first_name: "Contact 2"},
			{links: [
				[
					{link_doctype: "Customer"},
					{link_name: "Test Customer 2"}
				]
			]}
		],
	},
	"Price List": {
		"Test-Buying-USD": [
			{price_list_name: "Test-Buying-USD"},
			{currency: "USD"},
			{buying: "1"}
		],
		"Test-Buying-EUR": [
			{price_list_name: "Test-Buying-EUR"},
			{currency: "EUR"},
			{buying: "1"}
		],
		"Test-Selling-USD": [
			{price_list_name: "Test-Selling-USD"},
			{currency: "USD"},
			{selling: "1"}
		],
		"Test-Selling-EUR": [
			{price_list_name: "Test-Selling-EUR"},
			{currency: "EUR"},
			{selling: "1"}
		],
	},
	"Terms and Conditions": {
		"Test Term 1": [
			{title: "Test Term 1"}
		],
		"Test Term 2": [
			{title: "Test Term 2"}
		]
	}
});

// this is a script that creates all fixtures
// called as a test
QUnit.module('fixture');

QUnit.test('Make fixtures', assert => {
	// create all fixtures first
	assert.expect(0);
	let done = assert.async();
	let tasks = [];
	Object.keys(frappe.test_data).forEach(function(doctype) {
		tasks.push(function() { return frappe.tests.setup_doctype(doctype); });
	});
	frappe.run_serially(tasks).then(() => done());
});
