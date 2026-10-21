erpnext.PartyItems = class PartyItems {
	constructor(frm, { party_type, order_doctype, labels }) {
		this.frm = frm;
		this.party_type = party_type;
		this.order_doctype = order_doctype;
		this.labels = labels;
		this.method_path = "erpnext.selling.doctype.party_specific_item.party_specific_item";
		this.can = {
			read_orders: frappe.model.can_read("Item") && frappe.model.can_read(order_doctype),
			read_rules: frappe.model.can_read("Party Specific Item"),
			create_rules: frappe.model.can_create("Party Specific Item"),
			delete_rules: frappe.model.can_delete("Party Specific Item"),
		};
	}

	refresh() {
		const { frm, can } = this;
		frm.toggle_display("items_tab", can.read_orders || can.read_rules);
		frm.toggle_display("frequently_bought_html", can.read_orders);
		frm.toggle_display("party_specific_items_section", can.read_rules);
		this.needs_refresh = true;
		this.show();
	}

	async show() {
		if (!this.is_active() || !this.needs_refresh) return;
		await frappe.require("embedded_list.bundle.js");
		if (!this.is_active() || !this.needs_refresh) return;
		this.needs_refresh = false;
		this.party = this.frm.doc.name;

		if (this.can.read_orders) this.make_frequent_list();
		if (this.can.read_rules) this.make_rules_list();
	}

	is_active() {
		return this.frm.get_active_tab()?.df.fieldname === "items_tab";
	}

	make_frequent_list() {
		this.make_list("frequently_bought_html", {
			title: __("Frequently Bought"),
			description: this.labels.frequent_description,
			show_index: true,
			page_size: 5,
			show_search: false,
			empty_icon: "shopping-cart",
			empty_message: this.labels.frequent_empty,
			get_data: () => this.call("get_frequently_ordered_items"),
			columns: [...this.item_columns(), ...this.order_columns()],
		});
	}

	make_rules_list() {
		let rule_count = 0;
		this.rules_list = this.make_list("party_specific_items_html", {
			title: this.labels.section_title,
			description: this.labels.allowed_description,
			show_index: true,
			page_size: 10,
			empty_icon: "package",
			empty_message: this.labels.allowed_empty,
			get_data: () =>
				this.call("get_party_specific_items").then((rules) => {
					rule_count = this.rule_count = rules.length;
					return rules;
				}),
			after_render() {
				this.$wrapper.find("[data-action='search']").toggle(rule_count > this.page_size);
			},
			add_button: this.can.create_rules && {
				label: __("Add"),
				action: () => this.add_restriction(),
			},
			columns: [...this.rule_columns(), this.remove_rule_column()].filter(Boolean),
		});
	}

	rule_columns() {
		return [
			{ label: __("Value"), render: (row) => this.rule_name(row) },
			{
				label: __("Type"),
				render: (row) =>
					frappe.ui.badge.html({
						label: __(row.restrict_based_on),
						theme: { "Item Group": "blue", Brand: "violet", Item: "green" }[
							row.restrict_based_on
						],
					}),
			},
			{
				label: __("Covers"),
				align: "right",
				on_click: (row) => {
					if (row.restrict_based_on !== "Item" && row.item_count) this.show_rule_items(row);
				},
				render: (row) => {
					if (row.item_count == null) return "";
					if (!row.item_count) return `<span class="text-muted">${__("No items")}</span>`;
					if (row.restrict_based_on === "Item")
						return `<span class="text-muted">${this.count_label(1)}</span>`;
					return `<a href="#">${this.count_label(row.item_count)}</a>`;
				},
			},
		];
	}

	is_inherited(row) {
		return Boolean(row.party);
	}

	rule_name(row) {
		const escape = frappe.utils.escape_html;
		const href = frappe.utils.get_form_link(row.restrict_based_on, row.based_on_value);
		const is_item = row.restrict_based_on === "Item";
		const name = is_item && row.item_name ? row.item_name : row.based_on_value;
		const title = is_item ? ` title="${escape(row.based_on_value)}"` : "";
		let html = `<a href="${href}"${title}>${escape(name)}</a>`;
		if (this.is_inherited(row))
			html += ` <span class="text-muted">·</span> ${frappe.ui.badge.html({
				label: __(row.party_type),
				theme: "gray",
				title: `${__(row.party_type)}: ${row.party}`,
			})}`;
		return html;
	}

	add_restriction() {
		const descriptions = {
			Item: this.labels.item_hint,
			"Item Group": __("Covers every item in this group and its sub-groups."),
			Brand: __("Covers every item of this brand."),
		};
		const dialog = new frappe.ui.Dialog({
			title: this.labels.add_title,
			fields: [
				!this.rule_count && {
					fieldname: "first_rule_note",
					fieldtype: "HTML",
					options: `<p class="text-muted">${this.labels.first_rule_note}</p>`,
				},
				{
					fieldname: "restrict_based_on",
					fieldtype: "Select",
					label: __("Based On"),
					options: ["Item", "Item Group", "Brand"].map((value) => ({
						value,
						label: __(value),
					})),
					default: "Item",
					reqd: 1,
					onchange: () => {
						const based_on = dialog.get_value("restrict_based_on");
						dialog.set_value("based_on_value", "");
						dialog.set_df_property("based_on_value", "label", __(based_on));
						dialog.set_df_property("based_on_value", "description", descriptions[based_on]);
					},
				},
				{
					fieldname: "based_on_value",
					fieldtype: "Dynamic Link",
					label: __("Item"),
					options: "restrict_based_on",
					description: descriptions.Item,
					reqd: 1,
					get_query: () =>
						dialog.get_value("restrict_based_on") === "Item" ? this.item_query() : {},
				},
			].filter(Boolean),
			primary_action_label: __("Add"),
			primary_action: (values) =>
				frappe.db
					.insert({
						doctype: "Party Specific Item",
						party_type: this.party_type,
						party: this.party,
						...values,
					})
					.then(() => {
						dialog.hide();
						this.notify(
							__("Added {0} to {1}", [
								frappe.utils.escape_html(values.based_on_value),
								this.labels.section_title,
							])
						);
						this.rules_list.refresh();
					}),
		});
		dialog.show();
	}

	remove_restriction(row) {
		const name = frappe.utils.escape_html(row.item_name || row.based_on_value);
		frappe.confirm(__("Remove {0} from {1}?", [name, this.labels.section_title]), () =>
			frappe.db.delete_doc("Party Specific Item", row.name).then(() => {
				this.notify(__("Removed {0} from {1}", [name, this.labels.section_title]));
				this.rules_list.refresh();
			})
		);
	}

	show_rule_items(rule) {
		frappe.route_options =
			rule.restrict_based_on === "Brand"
				? { brand: rule.based_on_value, disabled: 0 }
				: { item_group: ["descendants of (inclusive)", rule.based_on_value], disabled: 0 };
		frappe.set_route("List", "Item");
	}

	show_orders(row) {
		frappe.route_options = {
			[frappe.scrub(this.party_type)]: this.party,
			item_code: row.name,
			docstatus: 1,
		};
		frappe.set_route("List", this.order_doctype);
	}

	item_columns() {
		return [
			{
				label: __("Item Code"),
				type: "link",
				fieldname: "name",
				route: (row) => ["Form", "Item", row.name],
			},
			{
				label: __("Item Name"),
				render: (row) =>
					frappe.utils.escape_html(row.item_name || "") +
					(row.disabled
						? " " + frappe.ui.badge.html({ label: __("Disabled"), theme: "gray" })
						: ""),
			},
		];
	}

	order_columns() {
		const none = `<span class="text-muted">—</span>`;
		return [
			{
				label: __("Orders"),
				title: this.labels.orders_title,
				align: "right",
				on_click: (row) => row.order_count && this.show_orders(row),
				render: (row) => (row.order_count ? `<a href="#">${row.order_count}</a>` : none),
			},
			{
				label: __("Last Ordered"),
				render: (row) => {
					const today = frappe.datetime.get_today();
					if (!row.last_ordered) return none;
					if (row.last_ordered === today) return __("Today");
					if (row.last_ordered > today) return frappe.datetime.str_to_user(row.last_ordered);
					return frappe.datetime.comment_when(row.last_ordered);
				},
			},
		];
	}

	remove_rule_column() {
		if (!this.can.delete_rules) return null;
		return {
			label: "",
			align: "right",
			on_click: (row) => {
				if (!this.is_inherited(row)) this.remove_restriction(row);
			},
			render: (row) =>
				this.is_inherited(row)
					? ""
					: `<span class="embedded-list-hover-reveal">${frappe.ui.button.html({
							icon: "trash",
							size: "xs",
							variant: "ghost",
							title: __("Remove"),
					  })}</span>`,
		};
	}

	make_list(fieldname, opts) {
		const list = new frappe.ui.EmbeddedList({
			wrapper: $("<div>").appendTo(this.frm.get_field(fieldname).$wrapper.empty()),
			...opts,
		});
		list.refresh();
		return list;
	}

	item_query() {
		return {
			query: `${this.method_path}.party_item_query`,
			filters: { party_type: this.party_type, party: this.party },
		};
	}

	call(method, args = {}) {
		return frappe.xcall(`${this.method_path}.${method}`, {
			party_type: this.party_type,
			party: this.party,
			...args,
		});
	}

	count_label(count) {
		return count === 1 ? __("1 item") : __("{0} items", [count]);
	}

	notify(message) {
		frappe.show_alert({ message, indicator: "green" });
	}
};
