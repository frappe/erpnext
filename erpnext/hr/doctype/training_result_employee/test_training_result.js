QUnit.module('hr');

QUnit.test("Test: Training Result [HR]", function (assert) {
	assert.expect(5);
	let done = assert.async();
	frappe.run_serially([
		// Creating Training Result
		() => frappe.set_route('List','Training Result','List'),
		() => frappe.timeout(0.3),
		() => frappe.click_button('Make a new Training Result'),
		() => {
			cur_frm.set_value('training_event','Test Training Event 1');
		},
		() => frappe.timeout(1),
		() => frappe.model.set_value('Training Result Employee','New Training Result Employee 1','hours',4),
		() => frappe.model.set_value('Training Result Employee','New Training Result Employee 1','grade','A'),
		() => frappe.model.set_value('Training Result Employee','New Training Result Employee 1','comments','Nice Seminar'),
		() => frappe.timeout(1),
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => cur_frm.save(),

		// Submitting the Training Result
		() => frappe.click_button('Submit'),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(4),

		// Checking if the fields are correctly set
		() => {
			assert.equal('Test Training Event 1',cur_frm.get_field('training_event').value,
				'Training Result is created');

			assert.equal('Test Employee 1',cur_frm.doc.employees[0].employee_name,
				'Training Result is created for correct employee');

			assert.equal(4,cur_frm.doc.employees[0].hours,
				'Hours field is correctly calculated');

			assert.equal('A',cur_frm.doc.employees[0].grade,
				'Grade field is correctly set');
		},

		() => frappe.set_route('List','Training Result','List'),
		() => frappe.timeout(2),

		// Checking the submission of Training Result
		() => {
			assert.ok(cur_list.data[0].docstatus==1,'Training Result Submitted successfully');
		},
		() => done()
	]);
});
