QUnit.module('Stock');

QUnit.test("test Batch", function(assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Batch', [
				{batch_id:'TEST-BATCH-001'},
				{item:'Test Product 4'},
				{expiry_date:frappe.datetime.add_days(frappe.datetime.now_date(), 2)},
			]);
		},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.batch_id=='TEST-BATCH-001', "Batch Id correct");
		},
		() => frappe.timeout(0.3),
		() => done()
	]);
});
