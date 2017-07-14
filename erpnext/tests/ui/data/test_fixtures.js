$.extend(frappe.test_data, {
	'Academic Year': 
	{
		'2016-17': [
			{academic_year_name: '2016-17'},
			{year_start_date: '2016-07-20'},
			{year_end_date: '2017-06-20'}
		]
	},
	'Academic Term': 
	{
		'2016-17 (Semester 1)': [
			{academic_year: '2016-17'},
			{term_name: 'Semester 1'},
			{term_start_date: '2016-07-20'},
			{term_end_date: '2017-06-20'}
		]
	},
	'Department': 
	{
		'Teaching': [
			{department_name: 'Teaching'}
		]
	},
	'Assessment Criteria Group': 
	{
		'Scholarship': [
			{assessment_criteria_group: 'Scholarship'}
		]
	},
	'Assessment Criteria': 
	{
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
	'Fee Category': {
		'Scholarship': [
			{category_name: 'Scholarship'},
			{description: 'Special Provision'}
		]
	},
	'Fee Structure': {
		'Standard Test': [
			{program: 'Standard Test'},
			{academic_term: '2016-17 (Semester 1)'},
			{student_category: 'Scholarship'},
			{components: [
				[
					{fees_category: 'Scholarship'},
					{amount: 20000}
				]
			]}
		]
	}
});