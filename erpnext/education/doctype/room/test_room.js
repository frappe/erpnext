// Testing Setup Module in Education
QUnit.module('education');

QUnit.test('Test: Room', function(assert){
	assert.expect(3);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Room', [
				{room_name: 'Room 1'},
				{room_number: '1'},
				{seating_capacity: '60'},
			]);
		},
		() => {
			assert.ok(cur_frm.doc.room_name == 'Room 1');
			assert.ok(cur_frm.doc.room_number = '1');
			assert.ok(cur_frm.doc.seating_capacity = '60');
		},
		() => done()
	]);
});
