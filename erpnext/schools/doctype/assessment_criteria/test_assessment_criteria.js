// School Assessment module
QUnit.module('schools');

QUnit.test('Test: Assessment Criteria', function(assert){
	assert.expect(0);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Assessment Criteria', [
				{assessment_criteria: 'Pass'},
				{assessment_criteria_group: 'Reservation'}
			]);
		},
		() => done()
	]);
});