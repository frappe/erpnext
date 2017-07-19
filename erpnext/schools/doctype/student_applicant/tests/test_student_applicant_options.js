QUnit.module('admission');

QUnit.test('test student applicant', function(assert){
	assert.expect(10);
	let done = assert.async();
	let testing_status;
	frappe.run_serially([
		() => frappe.tests.setup_doctype('Academic Year'),
		() => frappe.tests.setup_doctype('Academic Term'),
		() => frappe.tests.setup_doctype('Program'),
		() => frappe.tests.setup_doctype('Student Admission'),
		() => frappe.tests.setup_doctype('Student Applicant'),

		// Checking different options
		// 1. Moving forward with Submit
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => {
			testing_status = $('span.indicator.orange').text();
			assert.ok(testing_status.indexOf('Submit this document to confirm') == -1); // checking if submit has been successfull
		},

		// 2. Cancelling the Submit request
		() => frappe.tests.click_button('Cancel'),
		() => frappe.tests.click_button('Yes'),
		() => {
			testing_status = $('h1.editable-title').text();
			assert.ok(testing_status.indexOf('Cancelled') != -1); // checking if cancel request has been successfull
		},

		// 3. Checking Amend option
		() => frappe.tests.click_button('Amend'),
		() => cur_frm.doc.student_email_id = "test2@testmail.com", // updating email id since same id again is not allowed
		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'), // Submitting again after amend
		() => {
			testing_status = $('span.indicator.orange').text();
			assert.ok(testing_status.indexOf('Submit this document to confirm') == -1); // checking if submit has been successfull after amend
		},

		// Checking different Application status option
		() => cur_frm.set_value('application_status', "Applied"), // Applied Status
		() => frappe.tests.click_button('Update'),
		() => {
			testing_status = $('h1.editable-title').text();
			assert.ok(testing_status.indexOf('Applied') != -1); // checking if Applied has been successfull
		},
		() => cur_frm.set_value('application_status', "Rejected"), // Rejected Status
		() => frappe.tests.click_button('Update'),
		() => {
			testing_status = $('h1.editable-title').text();
			assert.ok(testing_status.indexOf('Rejected') != -1); // checking if Rejected has been successfull
		},
		() => cur_frm.set_value('application_status', "Admitted"), // Admitted Status
		() => frappe.tests.click_button('Update'),
		() => {
			testing_status = $('h1.editable-title').text();
			assert.ok(testing_status.indexOf('Admitted') != -1); // checking if Admitted has been successfull
		},
		() => cur_frm.set_value('application_status', "Approved"), // Approved Status
		() => frappe.tests.click_button('Update'),
		() => {
			testing_status = $('h1.editable-title').text();
			assert.ok(testing_status.indexOf('Approved') != -1); // checking if Approved has been successfull
		},

		// Clicking on Enroll button should add the applicant's entry in Student doctype, and take you to Program Enrollment page
		() => frappe.tests.click_button('Enroll'),
		() => {
			assert.ok(frappe.get_route()[0] == 'Form'); // Checking if the current page is Program Enrollment page or not
			assert.ok(frappe.get_route()[1] == 'Program Enrollment');
		},

		// Routing to Student List to check if the Applicant's entry has been made or not
		() => frappe.set_route('List', 'Student'),
		() => frappe.timeout(0.5),
		() => {$(`a:contains("Fname Mname Lname"):visible`).click();},
		() => frappe.timeout(0.5),
		() => {assert.ok(($(`h1.editable-title`).text()).indexOf('Enabled') != -1);}, // Checking if the Student entry has been enabled
		() => done()
	]);
});