// Education Assessment module
QUnit.module('education');

QUnit.test('Test: Assessment Group', function(assert){
	assert.expect(4);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route('Tree', 'Assessment Group'),

		// Checking adding child without selecting any Node
		() => frappe.tests.click_button('New'),
		() => frappe.timeout(0.2),
		() => {assert.equal($(`.msgprint`).text(), "Select a group node first.", "Error message success");},
		() => frappe.tests.click_button('Close'),
		() => frappe.timeout(0.2),

		// Creating child nodes
		() => frappe.tests.click_link('All Assessment Groups'),
		() => frappe.map_group.make('Assessment-group-1'),
		() => frappe.map_group.make('Assessment-group-4', "All Assessment Groups", 1),
		() => frappe.tests.click_link('Assessment-group-4'),
		() => frappe.map_group.make('Assessment-group-5', "Assessment-group-3", 0),

		// Checking Edit button
		() => frappe.timeout(0.5),
		() => frappe.tests.click_link('Assessment-group-1'),
		() => frappe.tests.click_button('Edit'),
		() => frappe.timeout(0.5),
		() => {assert.deepEqual(frappe.get_route(), ["Form", "Assessment Group", "Assessment-group-1"], "Edit route checks");},

		// Deleting child Node
		() => frappe.set_route('Tree', 'Assessment Group'),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_link('Assessment-group-1'),
		() => frappe.tests.click_button('Delete'),
		() => frappe.timeout(0.5),
		() => frappe.tests.click_button('Yes'),

		// Checking Collapse and Expand button
		() => frappe.timeout(2),
		() => frappe.tests.click_link('Assessment-group-4'),
		() => frappe.click_button('Collapse'),
		() => frappe.tests.click_link('All Assessment Groups'),
		() => frappe.click_button('Collapse'),
		() => {assert.ok($('.opened').size() == 0, 'Collapsed');},
		() => frappe.click_button('Expand'),
		() => {assert.ok($('.opened').size() > 0, 'Expanded');},

		() => done()
	]);
});

frappe.map_group = {
	make:function(assessment_group_name, parent_assessment_group = 'All Assessment Groups', is_group = 0){
		return frappe.run_serially([
			() => frappe.click_button('Add Child'),
			() => frappe.timeout(0.2),
			() => cur_dialog.set_value('is_group', is_group),
			() => cur_dialog.set_value('assessment_group_name', assessment_group_name),
			() => cur_dialog.set_value('parent_assessment_group', parent_assessment_group),
			() => frappe.click_button('Create New'),
		]);
	}
};