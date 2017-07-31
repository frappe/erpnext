// Testing Admission Module in Schools
QUnit.module('schools');

QUnit.test('Test: Student Admission', function(assert) {
	assert.expect(9);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Student Admission', [
				{academic_year: '2016-17'},
				{admission_start_date: '2016-04-20'},
				{admission_end_date: '2016-05-31'},
				{title: '2016-17 Admissions'},
				{program: 'Standard Test'},
				{application_fee: 1000},
				{naming_series_for_student_applicant: 'AP'},
				{introduction: 'Test intro'},
				{eligibility: 'Test eligibility'}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.academic_year == '2016-17');
			assert.ok(cur_frm.doc.admission_start_date == '2016-04-20');
			assert.ok(cur_frm.doc.admission_end_date == '2016-05-31');
			assert.ok(cur_frm.doc.title == '2016-17 Admissions');
			assert.ok(cur_frm.doc.program == 'Standard Test', 'Program correctly selected');
			assert.ok(cur_frm.doc.application_fee == 1000);
			assert.ok(cur_frm.doc.naming_series_for_student_applicant == 'AP');
			assert.ok(cur_frm.doc.introduction == 'Test intro');
			assert.ok(cur_frm.doc.eligibility == 'Test eligibility');
		},
		() => done()
	]);
});