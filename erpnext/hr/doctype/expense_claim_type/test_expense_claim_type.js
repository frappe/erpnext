QUnit.module('hr');

QUnit.test("Test: Expense claim type [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// create expense claim type
		() => {
			return frappe.tests.make('Expense Claim Type', [
				{expense_type: "Test Expense claim type"},
				{description: "This is just for testing"},
				{accounts: [
					[
						{company: "Test Company"},
						{default_account: "Expenses Included In Valuation - TC"}
					]
				]}
			]);
		},
		() => frappe.timeout(1),
		() => assert.equal("Test Expense claim type", cur_frm.doc.expense_type,
			"expense type correctly saved"),
		() => done()
	]);
});