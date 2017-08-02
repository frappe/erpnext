// Testing Admission module in Schools
QUnit.module('schools');

QUnit.test('test student applicant', function(assert){
	assert.expect(12);
	let done = assert.async();
	let testing_status;
	frappe.run_serially([
		() => frappe.set_route('Form', 'School House/New School House'),
		() => frappe.timeout(0.5),
		() => cur_frm.doc.house_name = 'Test_house',
		() => cur_frm.save(),
		() => frappe.set_route('List', 'Student Applicant'),
		() => frappe.timeout(0.5),
		() => {$(`a:contains("Fname Mname Lname"):visible`)[0].click();},

		// Checking different options
		// 1. Moving forward with Submit
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => {
			testing_status = $('span.indicator.orange').text();
			assert.ok(testing_status.indexOf('Submit this document to confirm') == -1); // checking if submit has been successfull
		},

		// 2. Cancelling the Submit request
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Cancel'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.5),
		() => {
			testing_status = $('h1.editable-title').text();
			assert.ok(testing_status.indexOf('Cancelled') != -1); // checking if cancel request has been successfull
		},

		// 3. Checking Amend option
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Amend'),
		() => cur_frm.doc.student_email_id = "test2@testmail.com", // updating email id since same id again is not allowed
		() => cur_frm.save(),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'), // Submitting again after amend
		() => {
			testing_status = $('span.indicator.orange').text();
			assert.ok(testing_status.indexOf('Submit this document to confirm') == -1); // checking if submit has been successfull after amend
		},

		// Checking different Application status option
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
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Enroll'),
		() => frappe.timeout(0.5),
		() => {
			assert.ok(frappe.get_route()[0] == 'Form'); // Checking if the current page is Program Enrollment page or not
			assert.ok(frappe.get_route()[1] == 'Program Enrollment');
		},

		// Routing to Student List to check if the Applicant's entry has been made or not
		() => frappe.timeout(0.5),
		() => frappe.set_route('List', 'Student'),
		() => frappe.timeout(0.5),
		() => {$(`a:contains("Fname Mname Lname"):visible`)[0].click();},
		() => frappe.timeout(0.5),
		() => {assert.ok(($(`h1.editable-title`).text()).indexOf('Enabled') != -1, 'Student entry successfully created');}, // Checking if the Student entry has been enabled
		// Enrolling the Student into a Program
		() => {$('.form-documents .row:nth-child(1) .col-xs-6:nth-child(1) .octicon-plus').click();},
		() => frappe.timeout(1),
		() => {
			cur_frm.set_value('program', 'Standard Test');
			cur_frm.set_value('student_category', 'Reservation');
			cur_frm.set_value('student_batch_name', 'A');
			cur_frm.set_value('academic_year', '2016-17');
			cur_frm.set_value('academic_term', '2016-17 (Semester 1)');
			cur_frm.set_value('school_house', 'Test_house');
			$('a:contains("Fees"):visible').click();
		},
		() => frappe.timeout(1),
		() => {
			cur_frm.doc.fees[0].student_category = "Reservation";
		},
		() => cur_frm.save(),
		// Submitting Program Enrollment form for our Test Student
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => {
			testing_status = $('.msgprint').text();
			assert.ok("Fee Records Created" == (testing_status.substring(0,19)), "Fee record created for enrolled student test");
		},
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Close'),
		() => {
			testing_status = $('h1').text();
			assert.ok(testing_status.indexOf('Submitted') != -1, "Program enrollment successfully submitted"); // Checking if the program enrollment entry shows submitted or not
		},
		() => done()
	]);
});