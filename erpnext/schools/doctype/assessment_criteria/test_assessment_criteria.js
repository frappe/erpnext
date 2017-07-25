QUnit.module('schools');

QUnit.test('test assessment criteria', function(assert){
	assert.expect(0);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Assessment Criteria', [
				{assessment_criteria: 'Pass'},
				{assessment_criteria_group: 'Scholarship'}
			]);
		},
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => done()
	]);
});