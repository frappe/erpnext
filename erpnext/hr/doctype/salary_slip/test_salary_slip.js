QUnit.test("test salary slip", function(assert) {
	assert.expect(3);
	let done = assert.async();
	let employee_name;
	frappe.run_serially([
		() => frappe.db.get_value('Employee', {'employee_name': 'Test Employee 1'}, 'name'),
		(r) => {
			employee_name = r.message.name;
		},
		() => {
			// Creating a salary slip for a employee
			frappe.tests.make('Salary Slip', [
				{ employee: employee_name}
			]);
		},
		() => frappe.timeout(5),
		() => {
			// To check if all the calculations are correctly done
			assert.ok(cur_frm.doc.gross_pay==42500,
				'Gross amount is correctly calculated'+cur_frm.doc.gross_pay);
			assert.ok(cur_frm.doc.total_deduction==7000,
				'Deduction amount is correctly calculated');
			assert.ok(cur_frm.doc.net_pay==35500,
				'Net amount is correctly calculated');
		},
		() => done()
	]);
});