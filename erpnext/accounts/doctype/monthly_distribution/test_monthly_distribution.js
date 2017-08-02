QUnit.module('Accounts');

QUnit.test("test monthly distribution", function(assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make("Monthly Distribution", [
				{distribution_id: "TEST MD 1"},
			]);
		},
		() => {assert.ok(cur_frm.doc.fiscal_year=='2017-2018');},
		() => done()
	]);
});

