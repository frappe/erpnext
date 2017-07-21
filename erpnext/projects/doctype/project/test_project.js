
QUnit.test("test project", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			// Creating project with task
			return frappe.tests.make('Project', [
				{ project_name: 'Test App'},
				{ expected_start_date: '2017-07-22'},
				{ expected_end_date: '2017-09-22'},
				{ estimated_costing: '10,000.00'},
				{ tasks:[
					[
						{title: 'Documentation'},
						{start_date: '2017-07-24'},
						{end_date: '2017-07-31'},
						{description: 'To make a proper documentation defining requirements etc'}
					]
				]}
			]);
		},
		// Retreiving random name generated against a task 
		() => frappe.db.get_value('Task', {'subject': 'Documentation'}, 'name'),
		(task) => {
			// Creating timesheet for a project
			return frappe.tests.make('Timesheet', [
				{ employee: 'EMP/0001'},
				{time_logs:[
					[
						{activity_type: 'Communication'},
						{from_time: '2017-07-24 13:00:00'},
						{to_time: '2017-07-24 15:00:00'},
						{hours: 2},
						{project: 'Test App'},
						{task: task.name},
						{billable: '1'},
						{billing_rate: 10},
						{costing_rate: 8}
					]
				]}
			]);
		},
		() => {
			// To check if a correct billable and costing amount is calculated
			assert.ok(cur_frm.get_field('total_billable_amount').get_value()==20,
				'Billable amount is correctly calculated');
			assert.ok(cur_frm.get_field('total_costing_amount').get_value()==16,
				'Costing amount is correctly calculated');
		},
		() => done()
	]);
});
