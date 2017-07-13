QUnit.module("sales");

QUnit.test("test: lead", function (assert) {
	assert.expect(1);
	let done = assert.async();
	let random = frappe.utils.get_random(10);
	frappe.run_serially([
		() => frappe.tests.setup_doctype("Lead"),
		() => frappe.set_route("List", "Lead"),
		() => frappe.new_doc("Lead"),
		() => cur_frm.set_value("lead_name", random),
		() => cur_frm.save(),
		() => {
			assert.ok(cur_frm.doc.lead_name.includes(random));
			return done();
		}
	]);
});
