// Testing Admission Module in Education
QUnit.module('education');

QUnit.test('Test: Student Admission', function(assert) {
	assert.expect(10);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Student Admission', [
				{academic_year: '2016-17'},
				{admission_start_date: '2016-04-20'},
				{admission_end_date: '2016-05-31'},
				{title: '2016-17 Admissions'},
				{enable_admission_application: 1},
				{introduction: 'Test intro'},
				{program_details: [
					[
						{'program': 'Standard Test'},
						{'application_fee': 1000},
						{'applicant_naming_series': 'AP'},
					]
				]}
			]);
		},
		() => cur_frm.save(),
		() => {
			assert.ok(cur_frm.doc.academic_year == '2016-17');
			assert.ok(cur_frm.doc.admission_start_date == '2016-04-20');
			assert.ok(cur_frm.doc.admission_end_date == '2016-05-31');
			assert.ok(cur_frm.doc.title == '2016-17 Admissions');
			assert.ok(cur_frm.doc.enable_admission_application == 1);
			assert.ok(cur_frm.doc.introduction == 'Test intro');
			assert.ok(cur_frm.doc.program_details[0].program == 'Standard Test', 'Program correctly selected');
			assert.ok(cur_frm.doc.program_details[0].application_fee == 1000);
			assert.ok(cur_frm.doc.program_details[0].applicant_naming_series == 'AP');
			assert.ok(cur_frm.doc.route == 'admissions/2016-17-Admissions', "Route successfully set");
		},
		() => done()
	]);
});