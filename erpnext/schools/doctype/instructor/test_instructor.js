// Testing Setup Module in Schools
QUnit.module('setup');

// Testing setting Instructor
QUnit.test('test instructor', function(assert){
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make("Instructor", [
				{instructor_name: 'Instructor 1'},
				{department: 'Teaching'}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.instructor_name == 'Instructor 1');
			assert.ok(cur_frm.doc.department = 'Teaching');
		},
		() => done()
	]);
});