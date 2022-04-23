// Testing Setup Module in Education
QUnit.module('education');

QUnit.test('Test: Student Category', function(assert){
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Student Category', [
				{category: 'Reservation'}
			]);
		},
		() => cur_frm.save(),
		() => {
			assert.ok(cur_frm.doc.name=='Reservation');
		},
		() => done()
	]);
});
