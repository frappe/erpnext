QUnit.module('hr');

QUnit.test("Test: Expense Claim [HR]", function (assert) {
	assert.expect(3);
	let done = assert.async();
	let employee_name;
	let d;
	frappe.run_serially([
		// Creating Expense Claim
		() => frappe.set_route('List','Expense Claim','List'),
		() => frappe.timeout(0.3),
		() => frappe.click_button('New'),
		() => {
			cur_frm.set_value('is_paid',1),
			cur_frm.set_value('expenses',[]),
			d = frappe.model.add_child(cur_frm.doc,'Expense Claim Detail','expenses'),
			d.expense_date = '2017-08-01',
			d.expense_type = 'Test Expense Type 1',
			d.description  = 'This is just to test Expense Claim',
			d.amount = 2000,
			d.sanctioned_amount=2000,
			refresh_field('expenses');
		},
		() => frappe.timeout(1),
		() => cur_frm.set_value('employee','Test Employee 1'),
		() => cur_frm.set_value('company','For Testing'),
		() => cur_frm.set_value('payable_account','Creditors - FT'),
		() => cur_frm.set_value('cost_center','Main - FT'),
		() => cur_frm.set_value('mode_of_payment','Cash'),
		() => cur_frm.save(),
		() => frappe.click_button('Submit'),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(3),

		// Checking if the amount is correctly reimbursed for the employee
		() => {
			assert.equal("Test Employee 1",cur_frm.doc.employee, 'Employee name set correctly');
			assert.equal(1, cur_frm.doc.is_paid, 'Expense is paid as required');
			assert.equal(2000, cur_frm.doc.total_amount_reimbursed, 'Amount is reimbursed correctly');

		},
		() => done()
	]);
});
