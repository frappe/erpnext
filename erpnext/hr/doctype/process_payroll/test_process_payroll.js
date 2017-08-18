QUnit.module('hr');

QUnit.test("Test: Process Payroll [HR]", function (assert) {
	assert.expect(5);
	let done = assert.async();
	let net_pay;

	let check_amounts = (employee_name,net_amt,gross_amt) => {
		frappe.run_serially([
			// Retrieving the actual amount from salary slip
			() => frappe.db.get_value('Salary Slip', {'employee_name': employee_name}, 'net_pay'),
			(r)	=> {
				net_pay=r.message.net_pay;
			},
			() => frappe.db.get_value('Salary Slip', {'employee_name': employee_name}, 'gross_pay'),

			// Checking if amounts are correctly calculated
			(r) => {
				assert.ok(net_pay==net_amt,
					'Net Pay is correctly calculated for '+employee_name);
				assert.ok(r.message.gross_pay==gross_amt,
					'Gross Pay is correctly calculated for '+employee_name);
			},
		]);
	};
	frappe.run_serially([

		// Deleting the already generated Salary Slips for employees
		() => frappe.set_route('List','Salary Slip'),
		() => frappe.timeout(2),
		() => { $('input.list-row-checkbox').click();},
		() => frappe.click_button('Delete'),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(2),
		() => assert.ok(cur_list.data.length==0,"Salary Slips successfully deleted"),
		() => frappe.timeout(3),


		// Creating Process Payroll for specific company
		() => frappe.set_route('Form','Process Payroll'),
		() => {
			cur_frm.set_value('company','Test Company'),
			frappe.timeout(1),
			cur_frm.set_value('payroll_frequency','Monthly'),
			cur_frm.set_value('start_date','2017-08-01'),
			frappe.timeout(1),
			cur_frm.set_value('end_date','2017-08-31'),
			cur_frm.set_value('cost_center','Main-TC'),
			frappe.timeout(1),
			frappe.click_button('Create Salary Slip');
		},
		() => frappe.timeout(3),
		() => check_amounts('Test Employee 1','19200','24000'),
		() => frappe.timeout(3),
		() => check_amounts('Test Employee 3','23040','28800'),
		() => frappe.timeout(4),
		() => done()
	]);
});
