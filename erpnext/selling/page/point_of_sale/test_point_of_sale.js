QUnit.test("test:Point of Sales", function(assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route('point-of-sale'),
		() => frappe.timeout(2),
		() => frappe.set_control('customer', 'Test Customer'),
		() => frappe.timeout(0.2),
		() => cur_frm.set_value('customer', 'Test Customer'),
		() => frappe.timeout(2),
		() => frappe.click_link('Test FG Item 2'),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.cart-items [title="_Test FG Item 2"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.number-pad [data-value="Rate"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.number-pad [data-value="2"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.number-pad [data-value="5"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.number-pad [data-value="0"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.number-pad [data-value="Pay"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.frappe-control [data-value="4"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.frappe-control [data-value="5"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_element(`.frappe-control [data-value="0"]`),
		() => frappe.timeout(0.2),
		() => frappe.click_button('Submit'),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(5),
		() => assert.ok(cur_frm.doc.docstatus==1, "Sales invoice created successfully"),
		() => done()
	]);
});