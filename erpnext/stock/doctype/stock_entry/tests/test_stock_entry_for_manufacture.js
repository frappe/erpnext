QUnit.module('Stock');

QUnit.test("test manufacture from bom", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make("Stock Entry", [
				{ purpose: "Manufacture" },
				{ from_bom: 1 },
				{ bom_no: "BOM-_Test Item - Non Whole UOM-001" },
				{ fg_completed_qty: 2 }
			]);
		},
		() => cur_frm.save(),
		() => frappe.click_button("Update Rate and Availability"),
		() => {
			assert.ok(cur_frm.doc.items[1] === 0.75, " Finished Item Qty correct");
			assert.ok(cur_frm.doc.items[2] === 0.25, " Process Loss Item Qty correct");
		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});
