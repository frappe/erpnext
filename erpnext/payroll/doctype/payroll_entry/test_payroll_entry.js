QUnit.module('HR');

QUnit.test("test: Payroll Entry", function (assert) {
	assert.expect(5);
	let done = assert.async();
	let employees, docname;

	frappe.run_serially([
		() => {
			return frappe.tests.make('Payroll Entry', [
				{company: 'For Testing'},
				{posting_date: frappe.datetime.add_days(frappe.datetime.nowdate(), 0)},
				{payroll_frequency: 'Monthly'},
				{cost_center: 'Main - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
			]);
		},

		() => frappe.timeout(1),
		() => {
			assert.equal(cur_frm.doc.company, 'For Testing');
			assert.equal(cur_frm.doc.posting_date, frappe.datetime.add_days(frappe.datetime.nowdate(), 0));
			assert.equal(cur_frm.doc.cost_center, 'Main - FT');
		},
		() => frappe.click_button('Get Employee Details'),
		() => {
			employees = cur_frm.doc.employees.length;
			docname = cur_frm.doc.name;
		},

		() => frappe.click_button('Submit'),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(5),

		() => frappe.click_button('View Salary Slip'),
		() => frappe.timeout(2),
		() => assert.equal(cur_list.data.length, employees),

		() => frappe.set_route('Form', 'Payroll Entry', docname),
		() => frappe.timeout(2),
		() => frappe.click_button('Submit Salary Slip'),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(5),

		() => frappe.click_button('Close'),
		() => frappe.timeout(1),

		() => frappe.click_button('View Salary Slip'),
		() => frappe.timeout(2),
		() => {
			let count = 0;
			for(var i = 0; i < employees; i++) {
				if(cur_list.data[i].docstatus == 1){
					count++;
				}
			}
			assert.equal(count, employees, "Salary Slip submitted for all employees");
		},

		() => done()
	]);
});
