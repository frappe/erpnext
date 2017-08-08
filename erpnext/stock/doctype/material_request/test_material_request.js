QUnit.module('Stock');

QUnit.test("test: material_request", function(assert) {
	assert.expect(10);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Material Request', [
				{material_request_type: 'Material Transfer'},
				{company: 'Test Company'},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"qty": 5},
						{"warehouse": 'All Warehouses - TC'},
						{"schedule_date": frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)}
					]]
				}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.material_request_type == 'Material Transfer', "Type correct");
			assert.ok(cur_frm.doc.company == 'Test Company', "Company correct");
			assert.ok(cur_frm.doc.items[0].item_code == 'Test Product 4', "Item correct");
			assert.ok(cur_frm.doc.items[0].item_name == 'Test Product 4', "Item name correct");
			assert.ok(cur_frm.doc.items[0].qty == 5, "Quantity correct");
			assert.ok(cur_frm.doc.items[0].warehouse == 'All Warehouses - TC', "Warehouse correct");
			assert.ok(cur_frm.doc.items[0].schedule_date == frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1));
		},
		() => frappe.timeout(0.3),
		() => cur_frm.print_doc(),
		() => frappe.timeout(1),
		() => {
			assert.ok($('.btn-print-print').is(':visible'), "Print Format Available");
			assert.ok($(".section-break+ .section-break .column-break:nth-child(1) .value").text().includes("Test Product 4"), "Print Preview Works");
		},
		() => cur_frm.print_doc(),
		() => frappe.click_button('Submit'),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => {
			assert.ok(cur_frm.doc.docstatus == 1, "Material request submitted");
		},
		() => done()
	]);
});