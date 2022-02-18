// Testing Attendance Module in Education
QUnit.module('education');

QUnit.test('Test: Student Attendance', function(assert){
	assert.expect(2);
	let done = assert.async();
	let student_code;

	frappe.run_serially([
		() => frappe.db.get_value('Student', {'student_email_id': 'test2@testmail.com'}, 'name'),
		(student) => {student_code = student.message.name;}, // fetching student code from db

		() => {
			return frappe.tests.make('Student Attendance', [
				{student: student_code},
				{date: frappe.datetime.nowdate()},
				{student_group: "test-batch-wise-group-2"},
				{status: "Absent"}
			]);
		},

		() => frappe.timeout(0.5),
		() => {assert.equal(cur_frm.doc.status, "Absent", "Attendance correctly saved");},

		() => frappe.timeout(0.5),
		() => cur_frm.set_value("status", "Present"),
		() => {assert.equal(cur_frm.doc.status, "Present", "Attendance correctly saved");},

		() => done()
	]);
});
