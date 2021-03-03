frappe.provide("erpnext.bundling");

$.extend(erpnext.bundling, {
	start_icon: '<i class="bundle-icon octicon octicon-package" style="color: rgb(152, 216, 91); font-size: 18px;"></i>',
	continue_icon: '<i class="bundle-icon octicon octicon-package" style="color: rgb(141, 153, 166); font-size: 18px;"></i>',
	terminate_icon: '<i class="bundle-icon octicon octicon-package" style="color: rgb(255, 160, 10); font-size: 18px;"></i>',

	setup_bundling: function (doctype) {
		frappe.ui.form.on(doctype, {
			refresh: function(frm) {
				erpnext.bundling.setup_bundle_buttons(frm);
				erpnext.bundling.render_bundle_icons(frm);
			},

			onload: function (frm) {
				frm.fields_dict.items.grid.wrapper.on('click', '.grid-row-check', () => erpnext.bundling.toggle_bundle_buttons(frm));
			}
		});

		frappe.ui.form.on(doctype + " Item", {
			items_move: function(frm, cdt, cdn) {
				erpnext.bundling.items_move_arrangement(frm);
				erpnext.bundling.validate_bundle_states(frm);
				erpnext.bundling.render_bundle_icons(frm);
			},
			items_add: function(frm) {
				erpnext.bundling.validate_bundle_states(frm);
				erpnext.bundling.render_bundle_icons(frm);
			},
			items_remove: function(frm) {
				erpnext.bundling.validate_bundle_states(frm);
				erpnext.bundling.render_bundle_icons(frm);
				erpnext.bundling.toggle_bundle_buttons(frm);
			}
		});
	},

	items_move_arrangement: function (frm) {
		let items = frm.doc.items;
		for(let i=0; i < items.length; i++) {
			let item = items[i];
			let item_prev = i > 0 ? items[i - 1] : null;
			let item_prev_of_prev = i > 0 ? items[i - 2] : null;
			let item_next = i < items.length - 1 ? items[i + 1] : null;
			let item_next_of_next = i < items.length - 1 ? items[i + 2] : null;
			let is_continue = false;

			if (item_prev && item_next && (item_prev.bundling_state == "Continue" && item.bundling_state == "Terminate" && item_next.bundling_state == "Continue")  ) {
				is_continue = item_next_of_next && (item_next_of_next.bundling_state != "" && item_next_of_next.bundling_state != "Start" && item_next_of_next.bundling_state != "Continue");
				if (is_continue){
					continue;
				} else {
					let temp_state = item.bundling_state;
					item.bundling_state = item_next.bundling_state;
					item_next.bundling_state = temp_state;
				}
			}
			if (item_prev && item_next && (item_prev.bundling_state == "Terminate" && item.bundling_state == "Start" && item_next.bundling_state == "Continue")) {
				is_continue = item_prev_of_prev && item_prev_of_prev.bundling_state == "Continue";
				if (is_continue) {
					continue;
				} else {
					let temp_state = item.bundling_state;
					item.bundling_state = item_prev.bundling_state;
					item_prev.bundling_state = temp_state;
				}
			}
			if (item_prev && item_next && (item_prev.bundling_state == "Start" && item.bundling_state == "Terminate" && item_next.bundling_state == "Continue")) {
				if (is_continue) {
					continue;
				} else {
					let temp_state = item.bundling_state;
					item.bundling_state = item_next.bundling_state;
					item_next.bundling_state = temp_state;
				}
			}
			if (item_prev && item_next && (item_prev.bundling_state == "Continue" && item.bundling_state == "Start" && item_next.bundling_state == "Continue")) {
				if (is_continue) {
					continue;
				} else {
					let temp_state = item.bundling_state;
					item.bundling_state = item_prev.bundling_state;
					item_prev.bundling_state = temp_state;
				}
			}
			if (item_prev && item_next && (item_prev.bundling_state == "Continue" && item.bundling_state == "Start" && item_next.bundling_state == "Terminate")) {
				if (is_continue) {
					continue;
				} else {
					let temp_state = item.bundling_state;
					item.bundling_state = item_prev.bundling_state;
				}
			}
			if (item_prev && item_next && (item_prev.bundling_state == "Continue" && item.bundling_state == "Terminate" && item_next.bundling_state == "Start")) {
				is_continue = item_next_of_next && (item_next_of_next.bundling_state == "Continue" || item_next_of_next.bundling_state == "Terminate");
				if (is_continue) {
					continue;
				}
				else {
					let temp_state = item.bundling_state;
					item.bundling_state = item_prev.bundling_state;
					item_next.bundling_state = temp_state;
				}
			}
		}
	},

	setup_bundle_buttons: function(frm) {
		frm.fields_dict.items.grid.add_custom_button(__("Unbundle"), () => erpnext.bundling.unbundle_selected(frm));
		frm.fields_dict.items.grid.custom_buttons[__("Unbundle")].addClass('hidden btn-warning');

		frm.fields_dict.items.grid.add_custom_button(__("Bundle"), () => erpnext.bundling.bundle_selected(frm));
		frm.fields_dict.items.grid.custom_buttons[__("Bundle")].addClass('hidden btn-success');
	},

	toggle_bundle_buttons: function (frm) {
		var checked = frm.fields_dict.items.grid.grid_rows.filter(row => row.doc.__checked);

		if (checked.length) {
			frm.fields_dict.items.grid.custom_buttons[__("Unbundle")].removeClass('hidden');
		} else {
			frm.fields_dict.items.grid.custom_buttons[__("Unbundle")].addClass('hidden');
		}

		if (checked.length > 1) {
			frm.fields_dict.items.grid.custom_buttons[__("Bundle")].removeClass('hidden');
		} else {
			frm.fields_dict.items.grid.custom_buttons[__("Bundle")].addClass('hidden');
		}
	},

	bundle_selected: function(frm) {
		erpnext.bundling.set_bundle_states(frm, "bundle");
		erpnext.bundling.validate_bundle_states(frm);
		erpnext.bundling.render_bundle_icons(frm);

		erpnext.bundling.deselect_all(frm);
		return false;
	},

	unbundle_selected: function(frm) {
		erpnext.bundling.set_bundle_states(frm, "unbundle");
		erpnext.bundling.validate_bundle_states(frm);
		erpnext.bundling.render_bundle_icons(frm);

		erpnext.bundling.deselect_all(frm);
		return false;
	},

	render_bundle_icons: function (frm) {
		$.each(frm.doc.items || [], function (i, item) {
			let wrapper = $(frm.fields_dict.items.grid.grid_rows[i].wrapper);

			if (item.bundling_state === "Start") {
				if($(wrapper.find('.bundle-icon').length)) {
					$(wrapper.find('.bundle-icon')[0]).remove();
				}
				$(wrapper.find('.grid-row-check')[0]).after(erpnext.bundling.start_icon);
			} else if (item.bundling_state === "Continue") {
				if($(wrapper.find('.bundle-icon').length)) {
					$(wrapper.find('.bundle-icon')[0]).remove();
				}
				$(wrapper.find('.grid-row-check')[0]).after(erpnext.bundling.continue_icon);
			} else if (item.bundling_state === "Terminate") {
				if($(wrapper.find('.bundle-icon').length)){
					$(wrapper.find('.bundle-icon')[0]).remove();
				}
				$(wrapper.find('.grid-row-check')[0]).after(erpnext.bundling.terminate_icon);
			} else {
				$(wrapper.find('.bundle-icon')[0]).remove();
			}
		});
	},

	deselect_all: function (frm) {
		$(frm.fields_dict.items.grid.wrapper).find('.grid-row-check:checked').prop('checked', '');

		$.each(frm.doc.items || [], function (i, item) {
			item.__checked = 0;
		});

		frm.refresh_field('items');
		erpnext.bundling.toggle_bundle_buttons(frm);
	},

	set_bundle_states: function (frm, action, selected) {
		if (!selected) {
			selected = frm.fields_dict.items.grid.get_selected_children();
		}

		if (action === "unbundle") {
			for (let i = 0; i < selected.length; i++) {
				selected[i].bundling_state = "";
			}
		} else {
			for (let i = 0; i < selected.length; i++) {
				if (i === 0) {
					selected[i].bundling_state = "Start";
				} else if (i === selected.length - 1) {
					selected[i].bundling_state = "Terminate";
				} else {
					selected[i].bundling_state = "Continue";
				}
			}
		}
		frm.dirty();
	},

	validate_bundle_states: function (frm) {
		let items = frm.doc.items;
		let bundle_start;
		let bundles = [];
		for(let i=0; i < items.length; i++) {
			let item = items[i];
			let item_prev = i > 0 ? items[i - 1] : null;
			let item_prev_of_prev = i > 0 ? items[i - 2] : null;
			let item_next = i < items.length - 1 ? items[i + 1] : null;
			let item_next_of_next = i < items.length - 1 ? items[i + 2] : null;
			let is_last = i === items.length - 1;

			if (["Start", "Continue"].includes(item.bundling_state) && !is_last) {
				if (bundle_start == null) {
					bundle_start = i;
				}
			}
			else {
				if (bundle_start != null) {
					let bundle_end = item.bundling_state === "Terminate" ? i : i - 1;
					bundles.push({bundle_start, bundle_end});
					bundle_start = null;
				}
				else if ((!item_prev || item_prev.bundling_state !== "Start") && ["Terminate", "Continue"].includes(item.bundling_state)) {
					item.bundling_state = ""
				}
			}
		}

		$.each(bundles, function (bi, b) {
			let bundle_size = b.bundle_end - b.bundle_start + 1;
			if (bundle_size <= 1) {
				if (bundle_size === 1) {
					items[b.bundle_start].bundling_state = "";
				}
			} else {
				let bundle_items = items.slice(b.bundle_start, b.bundle_end + 1);
				erpnext.bundling.set_bundle_states(frm, "bundle", bundle_items);
			}
		});

		return false;
	}
});