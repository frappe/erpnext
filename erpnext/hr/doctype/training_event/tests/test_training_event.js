QUnit.module('hr');

QUnit.test("Test: Training Event [HR]", function (assert) {
	assert.expect(5);
	let done = assert.async();
	let employee_name;

	frappe.run_serially([
		//  Creation of Training Event
		() => frappe.db.get_value('Employee', {'employee_name': 'Test Employee 1'}, 'name'),
		(r) => {
			employee_name = r.message.name;
		},
		() => {
			frappe.tests.make('Training Event', [
				{ event_name: 'Test Training Event 1'},
				{ location: 'Mumbai'},
				{ start_time: '2017-09-01 11:00:0'},
				{ end_time: '2017-09-01 17:00:0'},
				{ introduction: 'This is just a test'},
				{ employees: [
					[
						{employee: employee_name},
						{employee_name: 'Test Employee 1'},
						{attendance: 'Optional'}
					]
				]},
			]);
		},
		() => frappe.timeout(7),
		() => frappe.click_button('Submit'),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(8),
		() => {
			// To check if the fields are correctly set
			assert.ok(cur_frm.get_field('event_name').value == 'Test Training Event 1',
				'Event created successfully');

			assert.ok(cur_frm.get_field('event_status').value=='Scheduled',
				'Status of event is correctly set');

			assert.ok(cur_frm.doc.employees[0].employee_name=='Test Employee 1',
				'Attendee Employee is correctly set');

			assert.ok(cur_frm.doc.employees[0].attendance=='Optional',
				'Attendance is correctly set');
		},

		() => frappe.set_route('List','Training Event','List'),
		() => frappe.timeout(2),
		// Checking the submission of Training Event
		() => {
			assert.ok(cur_list.data[0].docstatus==1,'Training Event Submitted successfully');
		},
		() => frappe.timeout(2),
		() => done()
	]);
});