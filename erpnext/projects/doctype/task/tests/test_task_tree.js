/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Task Tree", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(4);

	frappe.run_serially([
		// insert a new Task
		() => frappe.set_route('Tree', 'Task'),
		() => frappe.timeout(0.5),

		// Checking adding child without selecting any Node
		() => frappe.tests.click_button('New'),
		() => frappe.timeout(0.5),
		() => {assert.equal($(`.msgprint`).text(), "Select a group node first.", "Error message success");},
		() => frappe.tests.click_button('Close'),
		() => frappe.timeout(0.5),

		// Creating child nodes
		() => frappe.tests.click_link('All Tasks'),
		() => frappe.map_group.make('Test-1'),
		() => frappe.map_group.make('Test-3', 1),
		() => frappe.timeout(1),
		() => frappe.tests.click_link('Test-3'),
		() => frappe.map_group.make('Test-4', 0),

		// Checking Edit button
		() => frappe.timeout(0.5),
		() => frappe.tests.click_link('Test-1'),
		() => frappe.tests.click_button('Edit'),
		() => frappe.timeout(1),
		() => frappe.db.get_value('Task', {'subject': 'Test-1'}, 'name'),
		(task) => {assert.deepEqual(frappe.get_route(), ["Form", "Task", task.message.name], "Edit route checks");},

		// Deleting child Node
		() => frappe.set_route('Tree', 'Task'),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_link('Test-1'),
		() => frappe.tests.click_button('Delete'),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Yes'),

		// Deleting Group Node that has child nodes in it
		() => frappe.timeout(0.5),
		() => frappe.tests.click_link('Test-3'),
		() => frappe.tests.click_button('Delete'),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(1),
		() => {assert.equal(cur_dialog.title, 'Message', 'Error thrown correctly');},
		() => frappe.tests.click_button('Close'),

		// Add multiple child tasks
		() => frappe.tests.click_link('Test-3'),
		() => frappe.timeout(0.5),
		() => frappe.click_button('Add Multiple'),
		() => frappe.timeout(1),
		() => cur_dialog.set_value('tasks', 'Test-6\nTest-7'),
		() => frappe.timeout(0.5),
		() => frappe.click_button('Submit'),
		() => frappe.timeout(2),
		() => frappe.click_button('Expand All'),
		() => frappe.timeout(1),
		() => {
			let count = $(`a:contains("Test-6"):visible`).length + $(`a:contains("Test-7"):visible`).length;
			assert.equal(count, 2, "Multiple Tasks added successfully");
		},

		() => done()
	]);
});

frappe.map_group = {
	make:function(subject, is_group = 0){
		return frappe.run_serially([
			() => frappe.click_button('Add Child'),
			() => frappe.timeout(1),
			() => cur_dialog.set_value('is_group', is_group),
			() => cur_dialog.set_value('subject', subject),
			() => frappe.click_button('Create New'),
			() => frappe.timeout(1.5)
		]);
	}
};
