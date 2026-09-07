context("Item Group selection", () => {
	let parent_group;
	let leaf_group;

	before(() => {
		cy.login();
		cy.visit("/desk/item");
		cy.window().then(async ({ frappe }) => {
			await frappe.model.with_doctype("Item");
			const parents = await frappe.db.get_list("Item Group", {
				filters: { is_group: 1 },
				limit: 1,
			});
			const leaves = await frappe.db.get_list("Item Group", {
				filters: { is_group: 0 },
				limit: 1,
			});
			parent_group = parents[0].name;
			leaf_group = leaves[0].name;
		});
	});

	it("allows parent groups in descendant filters", () => {
		cy.window().then(async ({ frappe, $ }) => {
			const $parent = $("<div>").appendTo("body");
			try {
				const filters = new frappe.ui.FilterGroup({
					parent: $parent,
					doctype: "Item",
					on_change: () => {},
				});
				await filters.add_filter("Item", "item_group", "descendants of", "");
				const field = filters.filters[0].field;
				const results = await frappe.xcall(
					"frappe.desk.search.search_link",
					field.get_search_args(parent_group)
				);
				expect(results.map((result) => result.value)).to.include(parent_group);
				await field.set_value(parent_group);
				expect(filters.get_filters()).to.deep.equal([
					["Item", "item_group", "descendants of", parent_group],
				]);
			} finally {
				$parent.remove();
			}
		});
	});

	it("restricts Quick Entry to leaf groups", () => {
		cy.window().then(async ({ frappe }) => {
			const dialog = await frappe.ui.form.make_quick_entry("Item", null, null, null, true);
			try {
				await check_leaf_group_selection(frappe, dialog.get_field("item_group"));
			} finally {
				dialog.hide();
			}
		});
	});

	it("restricts the full Item form to leaf groups", () => {
		cy.window().then(({ frappe }) => {
			const doc = frappe.model.get_new_doc("Item");
			return frappe.set_route("Form", "Item", doc.name);
		});
		cy.window().its("cur_frm.doctype").should("eq", "Item");
		cy.window().then(async ({ frappe, cur_frm }) => {
			await check_leaf_group_selection(frappe, cur_frm.get_field("item_group"));
		});
	});

	async function check_leaf_group_selection(frappe, field) {
		const parents = await frappe.xcall(
			"frappe.desk.search.search_link",
			field.get_search_args(parent_group)
		);
		expect(parents.map((result) => result.value)).not.to.include(parent_group);
		const leaves = await frappe.xcall(
			"frappe.desk.search.search_link",
			field.get_search_args(leaf_group)
		);
		expect(leaves.map((result) => result.value)).to.include(leaf_group);
	}
});
