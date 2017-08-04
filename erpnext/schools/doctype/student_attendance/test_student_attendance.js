// Testing Attendance Module in Schools
QUnit.module('schools');

QUnit.test('Test: Student Attendance', function(assert){
	assert.expect(2);
	let done = assert.async();
	let student_code;

	frappe.run_serially([
		() => frappe.set_route('List', 'Student'), // routing to Student list to fetch student code
		() => frappe.timeout(0.5),
		() => frappe.tests.click_link('Fname Mname Lname'),
		() => frappe.timeout(0.5),
		() => {student_code = frappe.get_route()[2];},

		() => {
			return frappe.tests.make('Student Attendance', [
				{student: student_code},
				{date: frappe.datetime.nowdate()},
				{student_group: "test-batch-wise-group-2"},
				{status: "Absent"}
			]);
		},

		() => frappe.timeout(0.5),
		() => {assert.equal(cur_frm.doc.status, "Absent", "Attendance correctly saved")},

		() => frappe.timeout(0.5),
		() => cur_frm.set_value("status", "Present"),
		() => {assert.equal(cur_frm.doc.status, "Present", "Attendance correctly saved")},

		() => done()
	]);
});