QUnit.test("test:POS Profile", function(assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make("POS Profile", [
				{naming_series: "SINV"},
				{company: "Test Company"},
				{country: "India"},
				{currency: "INR"},
				{write_off_account: "Write Off - TC"},
				{write_off_cost_center: "Main - TC"},
				{payments: [
					[
						{"default": 1},
						{"mode_of_payment": "Cash"}
					]]
				}
			]);
		},
		() => cur_frm.save(),
		() => frappe.timeout(2),
		() => {
			assert.equal(cur_frm.doc.payments[0].default, 1, "Default mode of payment tested");
		},
		() => done()
	]);
});

QUnit.test("test:Sales Invoice", function(assert) {
	assert.expect(2);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make("Sales Invoice", [
				{customer: "Test Customer 2"},
				{company: "Test Company"},
				{is_pos: 1},
				{posting_date: frappe.datetime.get_today()},
				{due_date: frappe.datetime.get_today()},
				{items: [
					[
						{"item_code": "Test Product 1"},
						{"qty": 5},
						{"warehouse":'Stores - TC'}
					]]
				}
			]);
		},
		() => frappe.timeout(2),
		() => cur_frm.save(),
		() => frappe.timeout(2),
		() => {
			assert.equal(cur_frm.doc.payments[0].default, 1, "Default mode of payment tested");
			assert.equal(cur_frm.doc.payments[0].mode_of_payment, "Cash", "Default mode of payment tested");
		},
		() => done()
	]);
});