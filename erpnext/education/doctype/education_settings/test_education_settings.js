/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

// Testing Setup Module in Education
QUnit.module('education');

QUnit.test("test: Education Settings", function (assert) {
	let done = assert.async();

	assert.expect(3);

	frappe.run_serially([
		() => frappe.set_route("List", "Education Settings"),
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
