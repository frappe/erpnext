// Testing Attendance Module in Education
QUnit.module('education');

QUnit.test('Test: Student Leave Application', function(assert){
	assert.expect(4);
	let done = assert.async();
	let student_code;
	let leave_code;
	frappe.run_serially([
		() => frappe.db.get_value('Student', {'student_email_id': 'test2@testmail.com'}, 'name'),
		(student) => {student_code = student.message.name;}, // fetching student code from db

		() => {
			return frappe.tests.make('Student Leave Application', [
				{student: student_code},
				{from_date: '2017-08-02'},
				{to_date: '2017-08-04'},
				{mark_as_present: 0},
				{reason: "Sick Leave."}
			]);
		},
		() => frappe.tests.click_button('Submit'), // Submitting the leave application
		() => frappe.timeout(0.7),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.7),
		() => {
			assert.equal(cur_frm.doc.docstatus, 1, "Submitted leave application");
			leave_code = frappe.get_route()[2];
		},
		() => frappe.tests.click_button('Cancel'), // Cancelling the leave application
		() => frappe.timeout(0.7),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1),
		() => {assert.equal(cur_frm.doc.docstatus, 2, "Cancelled leave application");},
		() => frappe.tests.click_button('Amend'), // Amending the leave application
		() => frappe.timeout(1),
		() => {
			cur_frm.doc.mark_as_present = 1;
			cur_frm.save();
		},
		() => frappe.timeout(0.7),
		() => frappe.tests.click_button('Submit'),
		() => frappe.timeout(0.7),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.7),
		() => {assert.equal(cur_frm.doc.amended_from, leave_code, "Amended successfully");},

		() => frappe.timeout(0.5),
		() => {
			return frappe.tests.make('Student Leave Application', [
				{student: student_code},
				{from_date: '2017-08-07'},
				{to_date: '2017-08-09'},
				{mark_as_present: 0},
				{reason: "Sick Leave."}
			]);
		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.timeout(0.7),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.7),
		() => {
			assert.equal(cur_frm.doc.docstatus, 1, "Submitted leave application");
			leave_code = frappe.get_route()[2];
		},

		() => done()
	]);
});
