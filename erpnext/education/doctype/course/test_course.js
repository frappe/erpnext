// Testing Setup Module in education
QUnit.module('education');

QUnit.test('test course', function(assert) {
	assert.expect(8);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Course', [
				{course_name: 'Test_Subject'},
				{course_code: 'Test_Sub'},
				{department: 'Test Department'},
				{course_abbreviation: 'Test_Sub'},
				{course_intro: 'Test Subject Intro'},
				{default_grading_scale: 'GTU'},
				{assessment_criteria: [
					[
						{assessment_criteria: 'Pass'},
						{weightage: 100}
					]
				]}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.course_name == 'Test_Subject', 'Course name correctly set');
			assert.ok(cur_frm.doc.course_code == 'Test_Sub', 'Course code correctly set');
			assert.ok(cur_frm.doc.department == 'Test Department', 'Department selected correctly');
			assert.ok(cur_frm.doc.course_abbreviation == 'Test_Sub');
			assert.ok(cur_frm.doc.course_intro == 'Test Subject Intro');
			assert.ok(cur_frm.doc.default_grading_scale == 'GTU', 'Grading scale selected correctly');
			assert.ok(cur_frm.doc.assessment_criteria[0].assessment_criteria == 'Pass', 'Assessment criteria selected correctly');
			assert.ok(cur_frm.doc.assessment_criteria[0].weightage == '100');
		},
		() => done()
	]);
});