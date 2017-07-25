QUnit.module('hr');

QUnit.test('test department', function(assert){
	assert.expect(0);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Department', [
				{department_name: 'Teaching'}
			]);
		},
		() => done()
	]);
});