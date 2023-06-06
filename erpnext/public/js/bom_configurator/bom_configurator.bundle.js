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
	}

	bind_events() {
		frappe.views.trees["BOM Configurator"].events = {
			add_item: this.add_item,
			add_sub_assembly: this.add_sub_assembly,
			get_sub_assembly_modal_fields: this.get_sub_assembly_modal_fields,
			convert_to_sub_assembly: this.convert_to_sub_assembly,
			delete_node: this.delete_node,
			edit_qty: this.edit_qty,
			frm: this.frm,
			// datatable: this.datatable,
		}
	}

	tree_options() {
		return {
			parent: this.$wrapper.get(0),
			body: this.$wrapper.get(0),
			doctype: 'BOM Configurator',
			page: this.page,
			expandable: true,
			title: __("Configure Product Assembly"),
			breadcrumb: "Manufacturing",
			get_tree_nodes: "erpnext.manufacturing.doctype.bom_configurator.bom_configurator.get_children",
			root_label: this.frm.doc.item_code,
			disable_add_node: true,
			get_tree_root: false,
			show_expand_all: false,
			extend_toolbar: false,
			do_not_make_page: true,
			do_not_setup_menu: true,
		}
	}

	tree_methods() {
		let frm_obj = this;
		let view = frappe.views.trees["BOM Configurator"];

		return {
			onload: function(me) {
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

				$(`<span class="pill small pull-right bom-qty-pill"
					style="background-color: var(--bg-gray);
						color: var(--text-on-gray);
						font-weight:500;
						margin-right: 10px;"
					data-bom-qty-docname="${docname}"
					>${qty} ${uom}</span>
				`).insertBefore(node.$ul);
			},
			toolbar: this.frm?.doc.docstatus === 0 ? [
				{
					label:__(frappe.utils.icon('edit', 'sm') + " Qty"),
					click: function(node) {
						let view = frappe.views.trees["BOM Configurator"];
						view.events.edit_qty(node);
					},
					btnClass: "hidden-xs"
				},
				{
					label:__(frappe.utils.icon('add', 'sm') + " Raw Material"),
					click: function(node) {
						let view = frappe.views.trees["BOM Configurator"];
						view.events.add_item(node);
					},
					condition: function(node) {
						return node.expandable;
					},
					btnClass: "hidden-xs"
				},
				{
					label:__(frappe.utils.icon('add', 'sm') + " Sub Assembly"),
					click: function(node) {
						let view = frappe.views.trees["BOM Configurator"];
						view.events.add_sub_assembly(node, view);
					},
					condition: function(node) {
						return node.expandable;
					},
					btnClass: "hidden-xs"
				},
				{
					label:__(frappe.utils.icon('move', 'sm') + " Sub Assembly"),
					click: function(node) {
						let view = frappe.views.trees["BOM Configurator"];
						view.events.convert_to_sub_assembly(node, view);
					},
					condition: function(node) {
						return !node.expandable;
					},
					btnClass: "hidden-xs"
				},
				{
					label:__(frappe.utils.icon('delete', 'sm') + __(" Item")),
					click: function(node) {
						let view = frappe.views.trees["BOM Configurator"];
						view.events.delete_node(node, view);
					},
					condition: function(node) {
						return !node.is_root;
					},
					btnClass: "hidden-xs"
				},
			] : [],
		}
	}

	add_item(node) {
		frappe.prompt([
			{ label: __("Item"), fieldname: "item_code", fieldtype: "Link", options: "Item", reqd: 1 },
			{ label: __("Qty"), fieldname: "qty", default: 1.0, fieldtype: "Float", reqd: 1 },
		],
		(data) => {
			if (!node.data.parent_id) {
				node.data.parent_id = this.frm.doc.name;
			}

			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_configurator.bom_configurator.add_item",
				args: {
					parent: node.data.parent_id,
					fg_item: node.data.value,
					item_code: data.item_code,
					qty: data.qty,
				},
				callback: (r) => {
					frappe.views.trees["BOM Configurator"].tree.load_children(node);
				}
			});
		},
		__("Add Item"),
		__("Add"));
	}

	add_sub_assembly(node, view) {
		let dialog = new frappe.ui.Dialog({
			fields: view.events.get_sub_assembly_modal_fields(),
			title: __("Add Sub Assembly"),
		});

		dialog.show();

		dialog.set_primary_action(__("Add"), () => {
			let bom_item = dialog.get_values();

			if (!node.data?.parent_id) {
				node.data.parent_id = this.frm.doc.name;
			}

			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_configurator.bom_configurator.add_sub_assembly",
				args: {
					parent: node.data.parent_id,
					fg_item: node.data.value,
					bom_item: bom_item,
				},
				callback: (r) => {
					frappe.views.trees["BOM Configurator"].tree.load_children(node);
					view.events.frm.doc = r.message;
				}
			});

			dialog.hide();
		});

	}

	get_sub_assembly_modal_fields(read_only=false) {
		return [
			{ label: __("Sub Assembly Item"), fieldname: "item_code", fieldtype: "Link", options: "Item", reqd: 1, read_only: read_only },
			{ fieldtype: "Column Break" },
			{ label: __("Qty"), fieldname: "qty", default: 1.0, fieldtype: "Float", reqd: 1, read_only: read_only },
			{ fieldtype: "Section Break" },
			{ label: __("Raw Materials"), fieldname: "items", fieldtype: "Table", reqd: 1,
				fields: [
					{ label: __("Item"), fieldname: "item_code", fieldtype: "Link", options: "Item", reqd: 1, in_list_view: 1 },
					{ label: __("Qty"), fieldname: "qty", default: 1.0, fieldtype: "Float", reqd: 1, in_list_view: 1 },
				]
			},
		]
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
		dialog.set_primary_action(__("Add"), () => {
			let bom_item = dialog.get_values();

			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_configurator.bom_configurator.add_sub_assembly",
				args: {
					parent: node.data.parent_id,
					fg_item: node.data.value,
					bom_item: bom_item,
					convert_to_sub_assembly: true,
				},
				callback: (r) => {
					node.expandable = true;
					frappe.views.trees["BOM Configurator"].tree.load_children(node);
					view.events.frm.doc = r.message;
				}
			});

			dialog.hide();
		});
	}

	delete_node(node, view) {
		frappe.confirm(__("Are you sure you want to delete this Item?"), () => {
			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_configurator.bom_configurator.delete_node",
				args: {
					parent: node.data.parent_id,
					fg_item: node.data.value,
					doctype: node.data.doctype,
					docname: node.data.name,
				},
				callback: (r) => {
					frappe.views.trees["BOM Configurator"].tree.load_children(node.parent_node);
				}
			});
		});
	}

	edit_qty(node) {
		let qty = node.data.qty || this.frm.doc.qty;
		frappe.prompt([
			{ label: __("Qty"), fieldname: "qty", default: qty, fieldtype: "Float", reqd: 1 },
		],
		(data) => {
			let doctype = node.data.doctype || this.frm.doc.doctype;
			let docname = node.data.name || this.frm.doc.name;

			frappe.call({
				method: "erpnext.manufacturing.doctype.bom_configurator.bom_configurator.edit_qty",
				args: {
					doctype: doctype,
					docname: docname,
					qty: data.qty,
				},
				callback: (r) => {
					node.data.qty = data.qty;
					let uom = node.data.uom || this.frm.doc.uom;
					$(node.parent.get(0)).find(`[data-bom-qty-docname='${docname}']`).html(data.qty + " " + uom);
				}
			});
		},
		__("Edit Qty"),
		__("Update"));
	}

	prepare_layout() {
		let main_div = $(this.page)[0];

		main_div.style.marginBottom = "15px";
		$(main_div).find(".tree-children")[0].style.minHeight = "370px";
		$(main_div).find(".tree-children")[0].style.maxHeight = "370px";
		$(main_div).find(".tree-children")[0].style.overflowY = "auto";
	}
}

frappe.ui.BOMConfigurator = BOMConfigurator;