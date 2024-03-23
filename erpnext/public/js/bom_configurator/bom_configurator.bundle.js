class BOMConfigurator {
	constructor({ wrapper, page, frm, bom_configurator }) {
		this.$wrapper = $(wrapper);
		this.page = page;
		this.bom_configurator = bom_configurator;
		this.frm = frm;

		this.make();
		this.prepare_layout();
		this.bind_events();
	}

	add_boms() {
		this.frm.call({
			method: "add_boms",
			freeze: true,
			doc: this.frm.doc,
		});
	}

	make() {
		let options = {
			...this.tree_options(),
			...this.tree_methods(),
		};

		frappe.views.trees["BOM Configurator"] = new frappe.views.TreeView(options);
		this.tree_view = frappe.views.trees["BOM Configurator"];
	}

	bind_events() {
		frappe.views.trees["BOM Configurator"].events = {
			frm: this.frm,
			add_item: this.add_item,
			add_sub_assembly: this.add_sub_assembly,
			get_sub_assembly_modal_fields: this.get_sub_assembly_modal_fields,
			convert_to_sub_assembly: this.convert_to_sub_assembly,
			delete_node: this.delete_node,
			edit_qty: this.edit_qty,
			load_tree: this.load_tree,
			set_default_qty: this.set_default_qty,
		};
	}

	tree_options() {
		return {
			parent: this.$wrapper.get(0),
			body: this.$wrapper.get(0),
			doctype: "BOM Configurator",
			page: this.page,
			expandable: true,
			title: __("Configure Product Assembly"),
			breadcrumb: "Manufacturing",
			get_tree_nodes: "erpnext.manufacturing.doctype.bom_creator.bom_creator.get_children",
			root_label: this.frm.doc.item_code,
			disable_add_node: true,
			get_tree_root: false,
			show_expand_all: false,
			extend_toolbar: false,
			do_not_make_page: true,
			do_not_setup_menu: true,
		};
	}

	tree_methods() {
		let frm_obj = this;
		let view = frappe.views.trees["BOM Configurator"];

		return {
			onload: function (me) {
				me.args["parent_id"] = frm_obj.frm.doc.name;
				me.args["parent"] = frm_obj.frm.doc.item_code;
				me.parent = frm_obj.$wrapper.get(0);
				me.body = frm_obj.$wrapper.get(0);
				me.make_tree();
			},
			onrender(node) {
				const qty = node.data.qty || frm_obj.frm.doc.qty;
				const uom = node.data.uom || frm_obj.frm.doc.uom;
				const docname = node.data.name || frm_obj.frm.doc.name;
				let amount = node.data.amount;
				if (node.data.value === frm_obj.frm.doc.item_code) {
					amount = frm_obj.frm.doc.raw_material_cost;
				}

				amount = frappe.format(amount, { fieldtype: "Currency", currency: frm_obj.frm.doc.currency });

				$(`
					<div class="pill small pull-right bom-qty-pill"
						style="background-color: var(--bg-white);
							color: var(--text-on-gray);
							font-weight:450;
							margin-right: 40px;
							display: inline-flex;
							min-width: 128px;
							border: 1px solid var(--bg-gray);
						">
							<div style="padding-right:5px" data-bom-qty-docname="${docname}">${qty} ${uom}</div>
							<div class="fg-item-amt" style="padding-left:12px; border-left:1px solid var(--bg-gray)">
								${amount}
							</div>
					</div>

				`).insertBefore(node.$ul);
			},
			toolbar:
				this.frm?.doc.docstatus === 0
					? [
							{
								label: `${frappe.utils.icon("edit", "sm")} ${__("Qty")}`,
								click: function (node) {
									let view = frappe.views.trees["BOM Configurator"];
									view.events.edit_qty(node, view);
								},
								btnClass: "hidden-xs",
							},
							{
								label: `${frappe.utils.icon("add", "sm")} ${__("Raw Material")}`,
								click: function (node) {
									let view = frappe.views.trees["BOM Configurator"];
									view.events.add_item(node, view);
								},
								condition: function (node) {
									return node.expandable;
								},
								btnClass: "hidden-xs",
							},
							{
								label: `${frappe.utils.icon("add", "sm")} ${__("Sub Assembly")}`,
								click: function (node) {
									let view = frappe.views.trees["BOM Configurator"];
									view.events.add_sub_assembly(node, view);
								},
								condition: function (node) {
									return node.expandable;
								},
								btnClass: "hidden-xs",
							},
							{
								label: __("Expand All"),
								click: function (node) {
									let view = frappe.views.trees["BOM Configurator"];

									if (!node.expanded) {
										view.tree.load_children(node, true);
										$(node.parent[0]).find(".tree-children").show();
										node.$toolbar.find(".expand-all-btn").html("Collapse All");
									} else {
										node.$tree_link.trigger("click");
										node.$toolbar.find(".expand-all-btn").html("Expand All");
									}
								},
								condition: function (node) {
									return node.expandable && node.is_root;
								},
								btnClass: "hidden-xs expand-all-btn",
							},
							{
								label: `${frappe.utils.icon("move", "sm")} ${__("Sub Assembly")}`,
								click: function (node) {
									let view = frappe.views.trees["BOM Configurator"];
									view.events.convert_to_sub_assembly(node, view);
								},
								condition: function (node) {
									return !node.expandable;
								},
								btnClass: "hidden-xs",
							},
							{
								label: `${frappe.utils.icon("delete", "sm")} ${__("Item")}`,
								click: function (node) {
									let view = frappe.views.trees["BOM Configurator"];
									view.events.delete_node(node, view);
								},
								condition: function (node) {
									return !node.is_root;
								},
								btnClass: "hidden-xs",
							},
					  ]
					: [
							{
								label: __("Expand All"),
								click: function (node) {
									let view = frappe.views.trees["BOM Configurator"];

									if (!node.expanded) {
										view.tree.load_children(node, true);
										$(node.parent[0]).find(".tree-children").show();
										node.$toolbar.find(".expand-all-btn").html("Collapse All");
									} else {
										node.$tree_link.trigger("click");
										node.$toolbar.find(".expand-all-btn").html("Expand All");
									}
								},
								condition: function (node) {
									return node.expandable && node.is_root;
								},
								btnClass: "hidden-xs expand-all-btn",
							},
					  ],
		};
	}

	add_item(node, view) {
		frappe.prompt(
			[
				{ label: __("Item"), fieldname: "item_code", fieldtype: "Link", options: "Item", reqd: 1 },
				{ label: __("Qty"), fieldname: "qty", default: 1.0, fieldtype: "Float", reqd: 1 },
			],
			(data) => {
				if (!node.data.parent_id) {
					node.data.parent_id = this.frm.doc.name;
				}

				frappe.call({
					method: "erpnext.manufacturing.doctype.bom_creator.bom_creator.add_item",
					args: {
						parent: node.data.parent_id,
						fg_item: node.data.value,
						item_code: data.item_code,
						fg_reference_id: node.data.name || this.frm.doc.name,
						qty: data.qty,
					},
					callback: (r) => {
						view.events.load_tree(r, node);
					},
				});
			},
			__("Add Item"),
			__("Add")
		);
	}

	add_sub_assembly(node, view) {
		let dialog = new frappe.ui.Dialog({
			fields: view.events.get_sub_assembly_modal_fields(),
			title: __("Add Sub Assembly"),
		});

		dialog.show();
		view.events.set_default_qty(dialog);

		dialog.set_primary_action(__("Add"), () => {
			let bom_item = dialog.get_values();

			if (!node.data?.parent_id) {
				node.data.parent_id = this.frm.doc.name;
			}

			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_creator.bom_creator.add_sub_assembly",
				args: {
					parent: node.data.parent_id,
					fg_item: node.data.value,
					fg_reference_id: node.data.name || this.frm.doc.name,
					bom_item: bom_item,
				},
				callback: (r) => {
					view.events.load_tree(r, node);
				},
			});

			dialog.hide();
		});
	}

	get_sub_assembly_modal_fields(read_only = false) {
		return [
			{
				label: __("Sub Assembly Item"),
				fieldname: "item_code",
				fieldtype: "Link",
				options: "Item",
				reqd: 1,
				read_only: read_only,
			},
			{ fieldtype: "Column Break" },
			{
				label: __("Qty"),
				fieldname: "qty",
				default: 1.0,
				fieldtype: "Float",
				reqd: 1,
				read_only: read_only,
			},
			{ fieldtype: "Section Break" },
			{
				label: __("Raw Materials"),
				fieldname: "items",
				fieldtype: "Table",
				reqd: 1,
				fields: [
					{
						label: __("Item"),
						fieldname: "item_code",
						fieldtype: "Link",
						options: "Item",
						reqd: 1,
						in_list_view: 1,
					},
					{
						label: __("Qty"),
						fieldname: "qty",
						default: 1.0,
						fieldtype: "Float",
						reqd: 1,
						in_list_view: 1,
					},
				],
			},
		];
	}

	convert_to_sub_assembly(node, view) {
		let dialog = new frappe.ui.Dialog({
			fields: view.events.get_sub_assembly_modal_fields(true),
			title: __("Add Sub Assembly"),
		});

		dialog.set_values({
			item_code: node.data.value,
			qty: node.data.qty,
		});

		dialog.show();
		view.events.set_default_qty(dialog);

		dialog.set_primary_action(__("Add"), () => {
			let bom_item = dialog.get_values();

			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_creator.bom_creator.add_sub_assembly",
				args: {
					parent: node.data.parent_id,
					fg_item: node.data.value,
					bom_item: bom_item,
					fg_reference_id: node.data.name || this.frm.doc.name,
					convert_to_sub_assembly: true,
				},
				callback: (r) => {
					node.expandable = true;
					view.events.load_tree(r, node);
				},
			});

			dialog.hide();
		});
	}

	set_default_qty(dialog) {
		dialog.fields_dict.items.grid.fields_map.item_code.onchange = function (event) {
			if (event) {
				let name = $(event.currentTarget).closest(".grid-row").attr("data-name");
				let item_row = dialog.fields_dict.items.grid.grid_rows_by_docname[name].doc;
				item_row.qty = 1;
				dialog.fields_dict.items.grid.refresh();
			}
		};
	}

	delete_node(node, view) {
		frappe.confirm(__("Are you sure you want to delete this Item?"), () => {
			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_creator.bom_creator.delete_node",
				args: {
					parent: node.data.parent_id,
					fg_item: node.data.value,
					doctype: node.data.doctype,
					docname: node.data.name,
				},
				callback: (r) => {
					view.events.load_tree(r, node.parent_node);
				},
			});
		});
	}

	edit_qty(node, view) {
		let qty = node.data.qty || this.frm.doc.qty;
		frappe.prompt(
			[{ label: __("Qty"), fieldname: "qty", default: qty, fieldtype: "Float", reqd: 1 }],
			(data) => {
				let doctype = node.data.doctype || this.frm.doc.doctype;
				let docname = node.data.name || this.frm.doc.name;

				frappe.call({
					method: "erpnext.manufacturing.doctype.bom_creator.bom_creator.edit_qty",
					args: {
						doctype: doctype,
						docname: docname,
						qty: data.qty,
						parent: node.data.parent_id,
					},
					callback: (r) => {
						node.data.qty = data.qty;
						let uom = node.data.uom || this.frm.doc.uom;
						$(node.parent.get(0))
							.find(`[data-bom-qty-docname='${docname}']`)
							.html(data.qty + " " + uom);
						view.events.load_tree(r, node);
					},
				});
			},
			__("Edit Qty"),
			__("Update")
		);
	}

	prepare_layout() {
		let main_div = $(this.page)[0];

		main_div.style.marginBottom = "15px";
		$(main_div).find(".tree-children")[0].style.minHeight = "370px";
		$(main_div).find(".tree-children")[0].style.maxHeight = "370px";
		$(main_div).find(".tree-children")[0].style.overflowY = "auto";
	}

	load_tree(response, node) {
		let item_row = "";
		let parent_dom = "";
		let total_amount = response.message.raw_material_cost;

		frappe.views.trees["BOM Configurator"].tree.load_children(node);

		while (node) {
			item_row = response.message.items.filter((item) => item.name === node.data.name);

			if (item_row?.length) {
				node.data.amount = item_row[0].amount;
				total_amount = node.data.amount;
			} else {
				total_amount = response.message.raw_material_cost;
			}

			parent_dom = $(node.parent.get(0));
			total_amount = frappe.format(total_amount, {
				fieldtype: "Currency",
				currency: this.frm.doc.currency,
			});

			$($(parent_dom).find(".fg-item-amt")[0]).html(total_amount);
			node = node.parent_node;
		}
	}
}

frappe.ui.BOMConfigurator = BOMConfigurator;
