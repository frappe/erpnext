QUnit.module('hr');

QUnit.test("Test: Expense claim [HR]", function (assert) {
	assert.expect(5);
	let done = assert.async();
	let today_date = frappe.datetime.nowdate();

	frappe.run_serially([
		// create expense claim
		() => frappe.db.get_value('Employee', {'employee_name':'Test Employee 1'}, 'name'),
		(employee) => {
			return frappe.tests.make('Expense Claim', [
				{exp_approver: "Test Expense claim"},
				{expenses: [
					[
						{expense_date: frappe.datetime.add_days(today_date, -1)},	// previous day
						{expense_type: "Test Expense claim type"},
						{description: "This is just for testing"},
						{claim_amount: 100}
					],
					[
						{expense_date: frappe.datetime.add_days(today_date, -2)},	// 2 days back
						{expense_type: "Test Expense claim type"},
						{description: "This is just for testing"},
						{claim_amount: 200}
					]
				]},
				{employee: employee.message.name}
			]);
		},
		() => frappe.timeout(1),
		() => {
			// check claim drafted or not
			assert.ok(!cur_frm.doc.docstatus,
				"expense claim is drafted and not saved before approval or rejection");
			// check total claim amount calculation
			assert.equal(300, cur_frm.doc.total_claimed_amount,
				"total claimed amount correctly set");
			// check total sanctioned amount calculation
			assert.equal(300, cur_frm.doc.total_sanctioned_amount,
				"total sanctioned amount correctly set");
		},
		() => cur_frm.set_value("approval_status", "Rejected"),
		() => frappe.timeout(0.5),
		() => cur_frm.save(),
		() => frappe.timeout(0.5),
		() => frappe.savesubmit(),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(0.5),
		() => {
			// check total sanctioned amount after rejection
			assert.equal(0, cur_frm.doc.total_sanctioned_amount,
				"rejecting claim made sanctioned amount zero");
			// check auto generate posting date
			assert.equal(today_date, cur_frm.doc.posting_date,
				"posting date set correctly");
		},
		() => done()
	]);
});