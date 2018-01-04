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
		() => frappe.click_button('Make a new Expense Claim'),
		() => {
			cur_frm.set_value('exp_approver','Administrator'),
			cur_frm.set_value('is_paid',1),
			cur_frm.set_value('expenses',[]),
			d = frappe.model.add_child(cur_frm.doc,'Expense Claim Detail','expenses'),
			d.expense_date = '2017-08-01',
			d.expense_type = 'Test Expense Type 1',
			d.description  = 'This is just to test Expense Claim',
			d.claim_amount = 2000,
			d.sanctioned_amount=2000,
			refresh_field('expenses');
		},
		() => frappe.timeout(2),
		() => frappe.db.get_value('Employee', {'employee_name': 'Test Employee 1'}, 'name'),
		(r) => {
			employee_name = r.message.name;
		},
		() => frappe.timeout(1),
		() => cur_frm.set_value('employee',employee_name),
		() => cur_frm.set_value('employee_name','Test Employee 1'),
		() => cur_frm.set_value('company','For Testing'),
		() => cur_frm.set_value('payable_account','Creditors - FT'),
		() => cur_frm.set_value('cost_center','Main - FT'),
		() => cur_frm.set_value('mode_of_payment','Cash'),
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => cur_frm.set_value('approval_status','Approved'),
		() => frappe.timeout(1),
		() => cur_frm.save(),
		// Submitting the Expense Claim
		() => frappe.click_button('Submit'),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(3),

		// Checking if the amount is correctly reimbursed for the employee
		() => {
			assert.equal(employee_name,cur_frm.get_field('employee').value,
				'Expense Claim is created for correct employee');
			assert.equal(1,cur_frm.get_field('is_paid').value,
				'Expense is paid as required');
			assert.equal(2000,cur_frm.get_field('total_amount_reimbursed').value,
				'Amount is reimbursed correctly');
		},
		() => done()
	]);
});

