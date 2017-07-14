// Testing Setup Module in Schools
QUnit.module('setup');

// Testing setting Batch Name
QUnit.test('test student batch name', function(assert){
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		// () => frappe.timeout(2),
		() => {
			return frappe.tests.make('Student Batch Name', [
					{batch_name: 'A'}
			]);
		},
		() => cur_frm.save(),
		() => {
			assert.ok(cur_frm.doc.batch_name=='A');
		},
		() => done()
	]);
});