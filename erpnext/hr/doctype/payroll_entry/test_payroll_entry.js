QUnit.module('HR')

QUnit.test("test: Payroll Entry", function (assert) {
	assert.expect(5);
	let done = assert.async();

	frappe.run_serially([
		() => {	
			return frappe.tests.make('Payroll Entry', [
				{company: 'For Testing'},
				{posting_date: frappe.datetime.add_days(frappe.datetime.nowdate(), 0)},
				{payroll_frequency: 'Monthly'},
				// {start_date: },
				{cost_center: 'Main - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
			]);
		},

		() => frappe.click_button('Submit'),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(2),

		() => {
			assert.equal(cur_frm.doc.company, 'For Testing');
			assert.equal(cur_frm.doc.posting_date, frappe.datetime.add_days(frappe.datetime.nowdate(), 0));
			assert.equal(cur_frm.doc.cost_center, 'Main - FT');
		},

		() => frappe.click_button('View Salary Slip'),
		() => frappe.timeout(2),
		() => assert.equal(cur_list.data[0].docstatus, 0),

		() => frappe.set_route('Form', 'Payroll Entry', 'Payroll 0041'),
		() => frappe.click_button('Submit Salary Slip'),
		() => frappe.timeout(2),

		() => frappe.click_button('Close'),
		() => frappe.timeout(1),

		() => frappe.click_button('View Salary Slip'),
		() => frappe.timeout(2),
		() => {
			 assert.ok(cur_list.data[0].docstatus == 1, "Salary slip submitted");
		},

		() => done()
	]);
});
