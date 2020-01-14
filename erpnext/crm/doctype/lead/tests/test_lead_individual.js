QUnit.module("sales");

QUnit.test("test: lead", function (assert) {
	assert.expect(4);
	let done = assert.async();
	let lead_name = frappe.utils.get_random(10);
	frappe.run_serially([
		// test lead creation
		() => frappe.set_route("List", "Lead"),
		() => frappe.new_doc("Lead"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("lead_name", lead_name),
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => {
			assert.ok(cur_frm.doc.lead_name.includes(lead_name),
				'name correctly set');
			frappe.lead_name = cur_frm.doc.name;
		},
		// create address and contact
		() => frappe.click_link('Address & Contact'),
		() => frappe.click_button('New Address'),
		() => frappe.timeout(1),
		() => frappe.set_control('address_line1', 'Gateway'),
		() => frappe.set_control('city', 'Mumbai'),
		() => cur_frm.save(),
		() => frappe.timeout(3),
		() => assert.equal(frappe.get_route()[1], 'Lead',
			'back to lead form'),
		() => frappe.click_link('Address & Contact'),
		() => assert.ok($('.address-box').text().includes('Mumbai'),
			'city is seen in address box'),

		// make opportunity
		() => frappe.click_button('Make'),
		() => frappe.click_link('Opportunity'),
		() => frappe.timeout(2),
		() => assert.equal(cur_frm.doc.lead, frappe.lead_name,
			'lead name correctly mapped'),

		() => done()
	]);
});
