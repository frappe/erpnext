// School Assessment module
QUnit.module('schools');

QUnit.test('Test: Grading Scale', function(assert){
	assert.expect(0);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Grading Scale', [
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
			]);
		},
		() => done()
	]);
});