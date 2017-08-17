QUnit.module('buying');

QUnit.test("Test: Request for Quotation", function (assert) {
	assert.expect(5);
	let done = assert.async();
	let rfq_name = "";

	frappe.run_serially([
		// Go to RFQ list
		() => frappe.set_route("List", "Request for Quotation"),
		// Create a new RFQ
		() => frappe.new_doc("Request for Quotation"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("transaction_date", "04-04-2017"),
		() => cur_frm.set_value("company", "_Test Company"),
		// Add Suppliers
		() => {
			cur_frm.fields_dict.suppliers.grid.grid_rows[0].toggle_view();
		},
		() => frappe.timeout(1),
		() => {
			cur_frm.fields_dict.suppliers.grid.grid_rows[0].doc.supplier = "_Test Supplier";
			frappe.click_check('Send Email');
			cur_frm.cur_grid.frm.script_manager.trigger('supplier');
		},
		() => frappe.timeout(1),
		() => {
			cur_frm.cur_grid.toggle_view();
		},
		() => frappe.timeout(1),
		() => frappe.click_button('Add Row',0),
		() => frappe.timeout(1),
		() => {
			cur_frm.fields_dict.suppliers.grid.grid_rows[1].toggle_view();
		},
		() => frappe.timeout(1),
		() => {
			cur_frm.fields_dict.suppliers.grid.grid_rows[1].doc.supplier = "_Test Supplier 1";
			frappe.click_check('Send Email');
			cur_frm.cur_grid.frm.script_manager.trigger('supplier');
		},
		() => frappe.timeout(1),
		() => {
			cur_frm.cur_grid.toggle_view();
		},
		() => frappe.timeout(1),
		// Add Item
		() => {
			cur_frm.fields_dict.items.grid.grid_rows[0].toggle_view();
		},
		() => frappe.timeout(1),
		() => {
			cur_frm.fields_dict.items.grid.grid_rows[0].doc.item_code = "_Test Item";
			frappe.set_control('item_code',"_Test Item");
			frappe.set_control('qty',5);
			frappe.set_control('schedule_date', "05-05-2017");
			cur_frm.cur_grid.frm.script_manager.trigger('supplier');
		},
		() => frappe.timeout(2),
		() => {
			cur_frm.cur_grid.toggle_view();
		},
		() => frappe.timeout(2),
		() => {
			cur_frm.fields_dict.items.grid.grid_rows[0].doc.warehouse = "_Test Warehouse - _TC";
		},
		() => frappe.click_button('Save'),
		() => frappe.timeout(1),
		() => frappe.click_button('Submit'),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),
		() => frappe.click_button('Menu'),
		() => frappe.timeout(1),
		() => frappe.click_link('Reload'),
		() => frappe.timeout(1),
		() => {
			assert.equal(cur_frm.doc.docstatus, 1);
			rfq_name = cur_frm.doc.name;
			assert.ok(cur_frm.fields_dict.suppliers.grid.grid_rows[0].doc.quote_status == "Pending");
			assert.ok(cur_frm.fields_dict.suppliers.grid.grid_rows[1].doc.quote_status == "Pending");
		},
		() => {
			cur_frm.fields_dict.suppliers.grid.grid_rows[0].toggle_view();
		},
		() => frappe.timeout(1),
		() => {
			frappe.click_check('No Quote');
		},
		() => frappe.timeout(1),
		() => {
			cur_frm.cur_grid.toggle_view();
		},
		() => frappe.click_button('Update'),
		() => frappe.timeout(1),

		() => frappe.click_button('Supplier Quotation'),
		() => frappe.timeout(1),
		() => frappe.click_link('Make'),
		() => frappe.timeout(1),
		() => {
			frappe.set_control('supplier',"_Test Supplier 1");
		},
		() => frappe.timeout(1),
		() => frappe.click_button('Make Supplier Quotation'),
		() => frappe.timeout(1),
		() => cur_frm.set_value("company", "_Test Company"),
		() => cur_frm.fields_dict.items.grid.grid_rows[0].doc.rate = 4.99,
		() => frappe.timeout(1),
		() => frappe.click_button('Save'),
		() => frappe.timeout(1),
		() => frappe.click_button('Submit'),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),
		() => frappe.set_route("List", "Request for Quotation"),
		() => frappe.timeout(2),
		() => frappe.set_route("List", "Request for Quotation"),
		() => frappe.timeout(2),
		() => frappe.click_link(rfq_name),
		() => frappe.timeout(1),
		() => frappe.click_button('Menu'),
		() => frappe.timeout(1),
		() => frappe.click_link('Reload'),
		() => frappe.timeout(1),
		() => {
			assert.ok(cur_frm.fields_dict.suppliers.grid.grid_rows[1].doc.quote_status == "Received");
			assert.ok(cur_frm.fields_dict.suppliers.grid.grid_rows[0].doc.no_quote == 1);
		},
		() => done()
	]);
});