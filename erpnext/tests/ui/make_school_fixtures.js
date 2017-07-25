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
	}
});

// this is a script that creates all fixtures
// called as a test
QUnit.module('fixture');

QUnit.test('Make School fixtures', assert => {
	// create all fixtures first
	assert.expect(0);
	let done = assert.async();
	let tasks = [];
	Object.keys(frappe.test_data).forEach(function(doctype) {
		tasks.push(function() { return frappe.tests.setup_doctype(doctype); });
	});
	frappe.run_serially(tasks).then(() => done());
});
