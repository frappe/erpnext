/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line
QUnit.module('Projects');

QUnit.test("test: Timesheet Creation Tool", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(5);

	frappe.run_serially([
		// insert a new Timesheet Creation Tool
		() => frappe.tests.make('Timesheet Creation Tool', [
			// values to be set
			{company: 'For Testing'},
			{employees: [
				[
					{"employee": 'EMP/0001'}
				],
				[
					{"employee": 'EMP/0005'}
				]
			]},
			{time_logs: [
				[
					{"activity_type": 'Planning'},
					{"from_time": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
					{"hours": 5},
					{"project": 'ERPNext Implementation'}
				],
				[
					{"activity_type": 'Communication'},
					{"from_time": frappe.datetime.add_days(frappe.datetime.now_date(), 7)},
					{"hours": 2},
					{"project": 'ERPNext Implementation'},
					{"billable": 1},
					{"billing_hours": 2},
					{"billing_rate": 100},
					{"costing_rate": 50}
				]
			]}
		]),
		() => {
			employees = cur_frm.doc.employees.length;
			assert.ok(cur_frm.doc.total_hours = 7, "hours correct");
			assert.ok(cur_frm.doc.total_billable_amount = 200, "billable amount correct");
			assert.ok(cur_frm.doc.total_costing_amount = 100, "total costing correct");
		},

		() => frappe.click_button('Create Timesheet as Draft'),
		() => frappe.timeout(3),
		() => frappe.set_route('List', 'Timesheet'),
		() => frappe.timeout(2),
		() => {
			for(var i = 0; i < employees; i++) {
				assert.equal(cur_list.data[i].start_date, frappe.datetime.add_days(frappe.datetime.now_date(), 5));
			}
		},

		() => done()
	]);

});
