// Testing Setup Module in Schools
QUnit.module('schools');

QUnit.test("Test: School Settings", function(assert){
	assert.expect(3);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.set_route("List", "School Settings"),
		() => frappe.timeout(0.4),
		() => {
			return frappe.tests.set_form_values(cur_frm, [
				{current_academic_year: '2016-17'},
				{current_academic_term: '2016-17 (Semester 1)'},
				{attendance_freeze_date: '2016-07-20'}
			]);
		},
		() => {
			cur_frm.save();
			assert.ok(cur_frm.doc.current_academic_year=="2016-17");
			assert.ok(cur_frm.doc.current_academic_term=="2016-17 (Semester 1)");
			assert.ok(cur_frm.doc.attendance_freeze_date=="2016-07-20");
		},
		() => done()
	]);
});