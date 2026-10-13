// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

erpnext.buying.setup_buying_controller();

frappe.ui.form.on("Request for Quotation", {
	setup: function (frm) {
		frm.fields_dict["suppliers"].grid.get_field("contact").get_query = function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				query: "frappe.contacts.doctype.contact.contact.contact_query",
				filters: {
					link_doctype: "Supplier",
					link_name: d.supplier || "",
				},
			};
		};

		frm.set_query("warehouse", "items", () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0,
			},
		}));
		frm.set_query("supplier", "suppliers", () => erpnext.queries.supplier(frm.doc));

		frm.set_indicator_formatter("item_code", function (doc) {
			return !doc.qty && frm.doc.has_unit_price_items ? "yellow" : "";
		});
	},

	refresh: function (frm, cdt, cdn) {
		frm.trigger("render_quotations_tab");

		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Supplier Quotation"),
				function () {
					frm.trigger("make_supplier_quotation");
				},
				__("Create")
			);

			frm.add_custom_button(
				__("Send Emails to Suppliers"),
				function () {
					frappe.call({
						method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.send_supplier_emails",
						freeze: true,
						args: {
							rfq_name: frm.doc.name,
						},
						callback: function (r) {
							frm.reload_doc();
						},
					});
				},
				__("Tools")
			);

			frm.add_custom_button(
				__("Download PDF"),
				() => {
					frappe.prompt(
						[
							{
								fieldtype: "Link",
								label: "Select a Supplier",
								fieldname: "supplier",
								options: "Supplier",
								reqd: 1,
								default: frm.doc.suppliers?.length == 1 ? frm.doc.suppliers[0].supplier : "",
								get_query: () => {
									return {
										filters: [
											[
												"Supplier",
												"name",
												"in",
												frm.doc.suppliers.map((row) => {
													return row.supplier;
												}),
											],
										],
									};
								},
							},
							{
								fieldtype: "Section Break",
								label: "Print Settings",
								fieldname: "print_settings",
								collapsible: 1,
							},
							{
								fieldtype: "Link",
								label: "Print Format",
								fieldname: "print_format",
								options: "Print Format",
								placeholder: "Standard",
								default: frappe.get_meta("Request for Quotation").default_print_format || "",
								get_query: () => {
									return {
										filters: {
											doc_type: "Request for Quotation",
										},
									};
								},
							},
							{
								fieldtype: "Link",
								label: "Language",
								fieldname: "language",
								options: "Language",
								default: frappe.boot.lang,
							},
							{
								fieldtype: "Link",
								label: "Letter Head",
								fieldname: "letter_head",
								options: "Letter Head",
								default: frm.doc.letter_head,
							},
						],
						(data) => {
							var w = window.open(
								frappe.urllib.get_full_url(
									"/api/method/erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_pdf?" +
										new URLSearchParams({
											name: frm.doc.name,
											supplier: data.supplier,
											print_format: data.print_format || "Standard",
											language: data.language || frappe.boot.lang,
											letterhead: data.letter_head || frm.doc.letter_head || "",
										}).toString()
								)
							);
							if (!w) {
								frappe.msgprint(__("Please enable pop-ups"));
								return;
							}
						},
						__("Download PDF for Supplier"),
						__("Download")
					);
				},
				__("Tools")
			);

			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}

		if (frm.doc.docstatus === 0) {
			erpnext.set_unit_price_items_note(frm);
		}
	},

	show_supplier_quotation_comparison(frm) {
		frappe.route_options = {
			company: frm.doc.company,
			from_date: moment(frm.doc.transaction_date).format("YYYY-MM-DD"),
			to_date: moment(new Date()).format("YYYY-MM-DD"),
			request_for_quotation: frm.doc.name,
		};
		frappe.set_route("query-report", "Supplier Quotation Comparison");
	},

	make_supplier_quotation: function (frm) {
		var doc = frm.doc;
		var dialog = new frappe.ui.Dialog({
			title: __("Create Supplier Quotation"),
			fields: [
				{
					fieldtype: "Link",
					label: __("Supplier"),
					fieldname: "supplier",
					options: "Supplier",
					reqd: 1,
					get_query: () => {
						return {
							filters: [
								[
									"Supplier",
									"name",
									"in",
									frm.doc.suppliers.map((row) => {
										return row.supplier;
									}),
								],
							],
						};
					},
				},
			],
			primary_action_label: __("Create"),
			primary_action: (args) => {
				if (!args) return;
				dialog.hide();

				return frappe.call({
					type: "GET",
					method: "erpnext.buying.doctype.request_for_quotation.mapper.make_supplier_quotation_from_rfq",
					args: {
						source_name: doc.name,
						for_supplier: args.supplier,
					},
					freeze: true,
					callback: function (r) {
						if (!r.exc) {
							var doc = frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					},
				});
			},
		});

		dialog.show();
	},

	toggle_quotations_tab: function (frm, show, quotes) {
		const $tab_li = frm.$wrapper.find(".form-tabs .nav-item").filter(function () {
			const text = $(this).text().trim();
			const fieldname = $(this).find(".nav-link").attr("data-fieldname");
			const href = $(this).find(".nav-link").attr("href") || "";
			return (
				text === __("Quotations") ||
				text === "Quotations" ||
				fieldname === "quotations_tab" ||
				href.includes("quotations")
			);
		});

		if (!show) {
			$tab_li.hide().addClass("hide hidden d-none").attr("style", "display: none !important;");
			if ($tab_li.find(".nav-link.active").length || $tab_li.hasClass("active")) {
				if (frm.layout && frm.layout.tabs && frm.layout.tabs[0]) {
					frm.layout.tabs[0].set_active();
				} else {
					frm.$wrapper.find(".form-tabs .nav-link").first().trigger("click");
				}
			}
			return;
		}

		if ($tab_li.length) {
			$tab_li.show().removeClass("hide hidden d-none").attr("style", "");
			if (
				frm.fields_dict &&
				frm.fields_dict.quotations_html &&
				frm.fields_dict.quotations_html.$wrapper
			) {
				frm.events.draw_quotations_comparison_table(
					frm,
					frm.fields_dict.quotations_html.$wrapper,
					quotes
				);
				return;
			}
		}
	},

	render_quotations_tab: function (frm) {
		if (frm.is_new()) {
			frm.events.toggle_quotations_tab(frm, false);
			return;
		}

		frm.events.toggle_quotations_tab(frm, false);
		const rfq_name = frm.doc.name;

		frappe.call({
			method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_supplier_quotations_data",
			args: { rfq_name: rfq_name },
			callback: function (r) {
				if (frm.doc.name !== rfq_name) {
					return;
				}

				const quotes = r.message || [];
				const has_quotes = Boolean(quotes && quotes.length > 0);
				frm.events.toggle_quotations_tab(frm, has_quotes, quotes);
			},
		});
	},

	draw_quotations_comparison_table: function (frm, $wrapper, quotes) {
		$wrapper.empty();

		const company_currency =
			(frm.doc.company && erpnext.get_currency(frm.doc.company)) ||
			frappe.boot.sysdefaults.currency ||
			"";

		// Each Supplier Quotation is a separate offer, so revised or alternative quotations
		// from the same supplier are compared side by side instead of being added together.
		const rfq_suppliers = (frm.doc.suppliers || []).map((s) => s.supplier).filter(Boolean);
		const offers = [];
		const offer_by_sq = {};
		(quotes || []).forEach((q) => {
			if (q.supplier_quotation && !offer_by_sq[q.supplier_quotation]) {
				offer_by_sq[q.supplier_quotation] = {
					key: q.supplier_quotation,
					supplier: q.supplier,
					supplier_quotation: q.supplier_quotation,
				};
				offers.push(offer_by_sq[q.supplier_quotation]);
			}
		});
		const supplier_order = (supplier) => {
			const idx = rfq_suppliers.indexOf(supplier);
			return idx === -1 ? rfq_suppliers.length : idx;
		};
		// stable sort: RFQ supplier order first, unlisted suppliers after, quotation date within a supplier
		offers.sort((a, b) => supplier_order(a.supplier) - supplier_order(b.supplier));

		const all_items = frm.doc.items || [];
		const selected_item = frm.quotations_item_filter || "";
		const items = selected_item ? all_items.filter((i) => i.item_code === selected_item) : all_items;

		const quote_map = {};
		const get_quote = (item, offer) => quote_map[`${item.name}:::${offer.key}`];
		const format_qty = (val) => (flt(val) % 1 === 0 ? cint(val) : flt(val, 2));

		function combine_quotes(item, matching_quotes) {
			if (!matching_quotes || matching_quotes.length === 0) return null;

			const rfq_item_conv = flt(item.conversion_factor) || 1.0;

			if (matching_quotes.length === 1) {
				const q = Object.assign({}, matching_quotes[0]);
				const sq_conv = flt(q.conversion_factor) || 1.0;
				const sq_base_rate = flt(q.base_rate) || flt(q.rate) * (flt(q.conversion_rate) || 1.0);
				const sq_base_amount = flt(q.base_amount) || flt(q.amount) * (flt(q.conversion_rate) || 1.0);

				q.converted_rate = (sq_base_rate / sq_conv) * rfq_item_conv;
				q.converted_amount = sq_base_amount;
				q.converted_qty =
					sq_conv === rfq_item_conv
						? flt(q.qty)
						: (flt(q.stock_qty) || flt(q.qty) * sq_conv) / rfq_item_conv;
				// quantity, rate and unit are all shown in the RFQ item's unit
				q.display_uom = item.uom || q.uom;
				q.quoted_as =
					q.uom && item.uom && q.uom !== item.uom
						? __("Quoted as {0} {1}", [format_qty(q.qty), q.uom])
						: "";
				q.supplier_quotations = [q.supplier_quotation].filter(Boolean);
				q.is_combined = false;
				return q;
			}

			// Several lines of the same Supplier Quotation for one RFQ item (e.g. split by rate
			// slabs) together make up a single offer, so their quantities and amounts are added
			let total_qty = 0;
			let total_base_amount = 0;
			const sq_names = [];
			const rate_breakdown = [];
			const hover_breakdown = [];

			matching_quotes.forEach((q) => {
				const q_qty = flt(q.qty);
				const sq_conv = flt(q.conversion_factor) || 1.0;
				const sq_base_rate = flt(q.base_rate) || flt(q.rate) * (flt(q.conversion_rate) || 1.0);
				const sq_base_amount = flt(q.base_amount) || flt(q.amount) * (flt(q.conversion_rate) || 1.0);
				const unit_rate = (sq_base_rate / sq_conv) * rfq_item_conv;
				const q_conv_qty =
					sq_conv === rfq_item_conv ? q_qty : (flt(q.stock_qty) || q_qty * sq_conv) / rfq_item_conv;

				total_qty += q_conv_qty;
				total_base_amount += sq_base_amount;

				if (q.supplier_quotation && !sq_names.includes(q.supplier_quotation)) {
					sq_names.push(q.supplier_quotation);
				}

				const rate_val = format_qty(unit_rate);
				const qty_val = format_qty(q_conv_qty);
				const uom = item.uom || q.uom || "";

				rate_breakdown.push(`${qty_val}-${rate_val}`);
				hover_breakdown.push(__("{0} {1} at {2} per {1}", [qty_val, uom, rate_val]));
			});

			const first = matching_quotes[0];
			const lead_times = matching_quotes.map((q) => cint(q.lead_time_days)).filter((d) => d > 0);
			return {
				item_code: item.item_code,
				item_name: item.item_name || first.item_name,
				supplier: first.supplier,
				supplier_quotation: sq_names.join(", "),
				supplier_quotations: sq_names,
				qty: total_qty,
				converted_qty: total_qty,
				uom: item.uom || first.uom,
				display_uom: item.uom || first.uom,
				quoted_as: "",
				stock_uom: first.stock_uom || item.stock_uom,
				conversion_factor: rfq_item_conv,
				converted_rate: total_qty > 0 ? total_base_amount / total_qty : 0,
				converted_amount: total_base_amount,
				rate_display: rate_breakdown.join(", "),
				rate_title: hover_breakdown.join(", "),
				lead_time_days: lead_times.length ? Math.max(...lead_times) : null,
				valid_till: first.valid_till,
				is_combined: true,
			};
		}

		// Map the lines of each offer to RFQ items
		offers.forEach((offer) => {
			const sup_quotes = (quotes || []).filter((q) => q.supplier_quotation === offer.key);

			const item_to_quotes = {};
			all_items.forEach((item) => {
				item_to_quotes[item.name] = [];
			});

			const unassigned_quotes = [];
			sup_quotes.forEach((q) => {
				if (q.request_for_quotation_item && item_to_quotes[q.request_for_quotation_item]) {
					item_to_quotes[q.request_for_quotation_item].push(q);
				} else {
					unassigned_quotes.push(q);
				}
			});

			// Group unassigned quotes by item_code
			const unassigned_by_code = {};
			unassigned_quotes.forEach((q) => {
				if (!unassigned_by_code[q.item_code]) {
					unassigned_by_code[q.item_code] = [];
				}
				unassigned_by_code[q.item_code].push(q);
			});

			Object.keys(unassigned_by_code).forEach((code) => {
				const code_quotes = unassigned_by_code[code];
				const rfq_items_with_code = all_items.filter((i) => i.item_code === code);

				if (rfq_items_with_code.length === 1) {
					item_to_quotes[rfq_items_with_code[0].name].push(...code_quotes);
				} else if (rfq_items_with_code.length > 1) {
					const empty_rfq_items = rfq_items_with_code.filter(
						(i) => item_to_quotes[i.name].length === 0
					);
					if (empty_rfq_items.length > 0) {
						code_quotes.forEach((q, idx) => {
							const target = empty_rfq_items[Math.min(idx, empty_rfq_items.length - 1)];
							item_to_quotes[target.name].push(q);
						});
					} else {
						item_to_quotes[rfq_items_with_code[0].name].push(...code_quotes);
					}
				}
			});

			all_items.forEach((item) => {
				const combined = combine_quotes(item, item_to_quotes[item.name]);
				if (combined) {
					quote_map[`${item.name}:::${offer.key}`] = combined;
				}
			});
		});

		// rates are all in company currency per RFQ unit, so they can be compared directly
		const min_rates = {};
		all_items.forEach((item) => {
			const rates = offers
				.map((offer) => get_quote(item, offer)?.converted_rate)
				.filter((r) => r !== undefined && r !== null && r > 0);
			if (rates.length > 0) {
				min_rates[item.name] = Math.min(...rates);
			}
		});

		all_items.forEach((item) => {
			const req_qty = flt(item.qty);
			offers.forEach((offer) => {
				const q = get_quote(item, offer);
				if (q) {
					const quoted_qty = q.converted_qty !== undefined ? flt(q.converted_qty) : flt(q.qty);
					if (req_qty > 0 && quoted_qty < req_qty) {
						q.is_partial_qty = true;
						q.partial_qty_tooltip = __("partial offer: {0} out of {1} qty", [
							format_qty(quoted_qty),
							format_qty(req_qty),
						]);
					} else {
						q.is_partial_qty = false;
						q.partial_qty_tooltip = "";
					}
				}
			});
		});

		const offer_pending_tooltips = {};
		offers.forEach((offer) => {
			// a zero qty line with a rate is a unit price offer, so the item counts as quoted
			const pending_items = all_items.filter((item) => {
				const q = get_quote(item, offer);
				if (!q || q.converted_amount === undefined || q.converted_amount === null) {
					return true;
				}
				return flt(q.qty) <= 0 && flt(q.converted_rate) <= 0;
			});

			if (pending_items.length > 0) {
				const pending_names = pending_items
					.map((i) => i.item_code || i.item_name)
					.filter(Boolean)
					.join(", ");
				offer_pending_tooltips[offer.key] = __("partial offer: {0} pending", [pending_names]);
			} else {
				offer_pending_tooltips[offer.key] = "";
			}
		});

		// only offers covering every shown item in full are eligible for the cheapest total
		const offer_totals = {};
		const complete_offers = [];
		const complete_offer_totals = [];
		offers.forEach((offer) => {
			let total = 0;
			let is_complete = true;
			let quoted_items_count = 0;
			items.forEach((item) => {
				const q = get_quote(item, offer);
				if (q && q.converted_amount !== undefined && q.converted_amount !== null && flt(q.qty) > 0) {
					total += flt(q.converted_amount);
					quoted_items_count++;

					const req_qty = flt(item.qty);
					const quoted_qty = q.converted_qty !== undefined ? flt(q.converted_qty) : flt(q.qty);
					if (req_qty > 0 && quoted_qty < req_qty) {
						is_complete = false;
					}
				} else {
					is_complete = false;
				}
			});
			if (quoted_items_count > 0) {
				offer_totals[offer.key] = total;
				if (is_complete && quoted_items_count === items.length) {
					complete_offers.push(offer.key);
					complete_offer_totals.push(total);
				}
			}
		});

		const min_offer_total = complete_offer_totals.length > 0 ? Math.min(...complete_offer_totals) : null;

		const quotation_count = offers.length;
		const categorize_by = quotation_count === 1 ? "Item" : frm.quotations_categorize_by || "Supplier";
		const has_quotes = quotes && quotes.length > 0;

		const context = {
			docstatus: frm.doc.docstatus,
			company_currency: company_currency,
			offers: offers,
			all_items: all_items,
			items: items,
			selected_item: selected_item,
			categorize_by: categorize_by,
			get_quote: get_quote,
			format_qty: format_qty,
			min_rates: min_rates,
			offer_totals: offer_totals,
			complete_offers: complete_offers,
			min_offer_total: min_offer_total,
			offer_pending_tooltips: offer_pending_tooltips,
			has_quotes: has_quotes,
			quotation_count: quotation_count,
		};

		const html = frappe.render_template("supplier_quotation_comparision", context);
		const $container = $(html).appendTo($wrapper);

		// Item Filter Control using Frappe UI Control
		if ($container.find(".item-filter-container").length) {
			const seen_codes = new Set();
			const unique_item_options = [];
			all_items.forEach((itm) => {
				if (!seen_codes.has(itm.item_code)) {
					seen_codes.add(itm.item_code);
					const label =
						itm.item_name && itm.item_name !== itm.item_code
							? `${itm.item_name} (${itm.item_code})`
							: itm.item_name || itm.item_code;
					unique_item_options.push({ label: label, value: itm.item_code });
				}
			});
			const item_options = [{ label: __("All Items"), value: "" }, ...unique_item_options];

			const item_control = frappe.ui.form.make_control({
				df: {
					fieldtype: "Select",
					fieldname: "quotations_item_filter",
					options: item_options,
					input_class: "input-sm",
					change: function () {
						const val = item_control.get_value() || "";
						if (val !== (frm.quotations_item_filter || "")) {
							frm.quotations_item_filter = val;
							frm.events.draw_quotations_comparison_table(frm, $wrapper, quotes);
						}
					},
				},
				parent: $container.find(".item-filter-container"),
				only_input: true,
			});
			item_control.set_value(selected_item || "");
			item_control.refresh();
			$(item_control.wrapper).css({ position: "relative", width: "100%", margin: "0" });
			$(item_control.wrapper).find(".select-icon").css({
				position: "absolute",
				right: "10px",
				top: "50%",
				transform: "translateY(-50%)",
				"pointer-events": "none",
			});
		}

		// Categorize By Control using Frappe UI Control
		if ($container.find(".categorize-by-filter-container").length) {
			if (quotation_count === 1) {
				$container.find(".categorize-by-filter-container").hide();
			} else {
				$container.find(".categorize-by-filter-container").show();
				const categorize_control = frappe.ui.form.make_control({
					df: {
						fieldtype: "Select",
						fieldname: "quotations_categorize_by",
						options: [
							{ label: __("Categorize by Supplier"), value: "Supplier" },
							{ label: __("Categorize by Item"), value: "Item" },
						],
						input_class: "input-sm",
						change: function () {
							const val = categorize_control.get_value() || "Supplier";
							if (val !== (frm.quotations_categorize_by || "Supplier")) {
								frm.quotations_categorize_by = val;
								frm.events.draw_quotations_comparison_table(frm, $wrapper, quotes);
							}
						},
					},
					parent: $container.find(".categorize-by-filter-container"),
					only_input: true,
				});
				categorize_control.set_value(categorize_by || "Supplier");
				categorize_control.refresh();
				$(categorize_control.wrapper).css({ position: "relative", width: "100%", margin: "0" });
				$(categorize_control.wrapper).find(".select-icon").css({
					position: "absolute",
					right: "10px",
					top: "50%",
					transform: "translateY(-50%)",
					"pointer-events": "none",
				});
			}
		}

		$container.find(".btn-new-supplier-quotation").on("click", function () {
			frm.trigger("make_supplier_quotation");
		});
	},

	schedule_date(frm) {
		if (frm.doc.schedule_date) {
			frm.doc.items.forEach((item) => {
				item.schedule_date = frm.doc.schedule_date;
			});
		}
		refresh_field("items");
	},

	email_template(frm) {
		if (frm.doc.email_template) {
			frappe.db
				.get_value("Email Template", frm.doc.email_template, [
					"use_html",
					"response",
					"response_html",
					"subject",
				])
				.then((r) => {
					if (r.message.use_html) {
						frm.set_value({
							mfs_html: r.message.response_html,
							use_html: 1,
						});
					} else {
						frm.set_value({
							message_for_supplier: r.message.response,
							use_html: 0,
						});
					}
					frm.set_value("subject", r.message.subject);
				});
		}
	},
	preview: (frm) => {
		let dialog = new frappe.ui.Dialog({
			title: __("Preview Email"),
			fields: [
				{
					label: __("Supplier"),
					fieldtype: "Select",
					fieldname: "supplier",
					options: frm.doc.suppliers.map((row) => row.supplier),
					reqd: 1,
				},
				{
					fieldtype: "Column Break",
					fieldname: "col_break_1",
				},
				{
					label: __("Subject"),
					fieldtype: "Data",
					fieldname: "subject",
					read_only: 1,
					depends_on: "subject",
				},
				{
					fieldtype: "Section Break",
					fieldname: "sec_break_1",
					hide_border: 1,
				},
				{
					label: __("Email"),
					fieldtype: "HTML",
					fieldname: "email_preview",
				},
				{
					fieldtype: "Section Break",
					fieldname: "sec_break_2",
				},
				{
					label: __("Note"),
					fieldtype: "HTML",
					fieldname: "note",
				},
			],
		});

		dialog.fields_dict["supplier"].df.onchange = () => {
			frm.call("get_supplier_email_preview", {
				supplier: dialog.get_value("supplier"),
			}).then(({ message }) => {
				dialog.fields_dict.email_preview.$wrapper.empty();
				dialog.fields_dict.email_preview.$wrapper.append(message.message);
				dialog.set_value("subject", message.subject);
			});
		};

		const msg = __(
			"This is a preview of the email to be sent. A PDF of the document will automatically be attached with the email."
		);
		dialog.fields_dict.note.$wrapper.append(`<p class="small text-muted">${msg}</p>`);

		dialog.show();
	},
});
frappe.ui.form.on("Request for Quotation Item", {
	items_add(frm, cdt, cdn) {
		if (frm.doc.schedule_date) {
			frappe.model.set_value(cdt, cdn, "schedule_date", frm.doc.schedule_date);
		}
	},
});
frappe.ui.form.on("Request for Quotation Supplier", {
	supplier: function (frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		frappe.call({
			method: "erpnext.accounts.party.get_party_details",
			args: {
				party: d.supplier,
				party_type: "Supplier",
				company: frm.doc.company,
			},
			callback: function (r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, "contact", r.message.contact_person);
					frappe.model.set_value(cdt, cdn, "email_id", r.message.contact_email);
				}
			},
		});
	},
});

erpnext.buying.RequestforQuotationController = class RequestforQuotationController extends (
	erpnext.buying.BuyingController
) {
	refresh() {
		var me = this;
		super.refresh();
		if (this.frm.doc.docstatus === 0) {
			this.frm.add_custom_button(
				__("Material Request"),
				function () {
					erpnext.utils.map_current_doc({
						method: "erpnext.stock.doctype.material_request.mapper.make_request_for_quotation",
						source_doctype: "Material Request",
						target: me.frm,
						setters: {
							schedule_date: undefined,
							status: undefined,
						},
						get_query_filters: {
							material_request_type: "Purchase",
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_ordered: ["<", 100],
							company: me.frm.doc.company,
						},
					});
				},
				__("Get Items From")
			);

			// Get items from Opportunity
			this.frm.add_custom_button(
				__("Opportunity"),
				function () {
					erpnext.utils.map_current_doc({
						method: "erpnext.crm.doctype.opportunity.mapper.make_request_for_quotation",
						source_doctype: "Opportunity",
						target: me.frm,
						setters: {
							party_name: undefined,
							opportunity_from: undefined,
							status: undefined,
						},
						get_query_filters: {
							status: ["not in", ["Closed", "Lost"]],
							company: me.frm.doc.company,
						},
					});
				},
				__("Get Items From")
			);

			// Get items from open Material Requests based on supplier
			this.frm.add_custom_button(
				__("Possible Supplier"),
				function () {
					// Create a dialog window for the user to pick their supplier
					var dialog = new frappe.ui.Dialog({
						title: __("Select Possible Supplier"),
						fields: [
							{
								fieldname: "supplier",
								fieldtype: "Link",
								options: "Supplier",
								label: "Supplier",
								reqd: 1,
								description: __("Get Items from Material Requests against this Supplier"),
							},
						],
						primary_action_label: __("Get Items"),
						primary_action: (args) => {
							if (!args) return;
							dialog.hide();

							erpnext.utils.map_current_doc({
								method: "erpnext.buying.doctype.request_for_quotation.mapper.get_item_from_material_requests_based_on_supplier",
								source_name: args.supplier,
								target: me.frm,
								setters: {
									company: me.frm.doc.company,
								},
								get_query_filters: {
									material_request_type: "Purchase",
									docstatus: 1,
									status: ["!=", "Stopped"],
									per_ordered: ["<", 100],
								},
							});
							dialog.hide();
						},
					});

					dialog.show();
				},
				__("Get Items From")
			);

			// Link Material Requests
			this.frm.add_custom_button(
				__("Link to Material Requests"),
				function () {
					erpnext.buying.link_to_mrs(me.frm);
				},
				__("Tools")
			);

			// Get Suppliers
			this.frm.add_custom_button(
				__("Get Suppliers"),
				function () {
					me.get_suppliers_button(me.frm);
				},
				__("Tools")
			);
		}
	}

	calculate_taxes_and_totals() {
		return;
	}

	tc_name() {
		this.get_terms();
	}

	get_suppliers_button(frm) {
		var doc = frm.doc;
		var dialog = new frappe.ui.Dialog({
			title: __("Get Suppliers"),
			fields: [
				{
					fieldtype: "Select",
					label: __("Get Suppliers By"),
					fieldname: "search_type",
					options: ["Supplier Group", "Tag"],
					reqd: 1,
					onchange() {
						if (dialog.get_value("search_type") == "Tag") {
							frappe
								.call({
									method: "erpnext.buying.doctype.request_for_quotation.request_for_quotation.get_supplier_tag",
								})
								.then((r) => {
									dialog.set_df_property("tag", "options", r.message);
								});
						}
					},
				},
				{
					fieldtype: "Link",
					label: __("Supplier Group"),
					fieldname: "supplier_group",
					options: "Supplier Group",
					reqd: 0,
					depends_on: "eval:doc.search_type == 'Supplier Group'",
				},
				{
					fieldtype: "Select",
					label: __("Tag"),
					fieldname: "tag",
					reqd: 0,
					depends_on: "eval:doc.search_type == 'Tag'",
				},
			],
			primary_action_label: __("Add Suppliers"),
			primary_action: (args) => {
				if (!args) return;
				dialog.hide();

				//Remove blanks
				for (var j = 0; j < frm.doc.suppliers.length; j++) {
					if (!Object.prototype.hasOwnProperty.call(frm.doc.suppliers[j], "supplier")) {
						frm.get_field("suppliers").grid.grid_rows[j].remove();
					}
				}

				function load_suppliers(r) {
					if (r.message) {
						for (var i = 0; i < r.message.length; i++) {
							var exists = false;
							let supplier = "";
							if (r.message[i].constructor === Array) {
								supplier = r.message[i][0];
							} else {
								supplier = r.message[i].name;
							}

							for (var j = 0; j < doc.suppliers.length; j++) {
								if (supplier === doc.suppliers[j].supplier) {
									exists = true;
								}
							}
							if (!exists) {
								var d = frm.add_child("suppliers");
								d.supplier = supplier;
								frm.script_manager.trigger("supplier", d.doctype, d.name);
							}
						}
					}
					frm.refresh_field("suppliers");
				}

				if (args.search_type === "Tag" && args.tag) {
					return frappe.call({
						type: "GET",
						method: "frappe.desk.doctype.tag.tag.get_tagged_docs",
						args: {
							doctype: "Supplier",
							tag: "%" + args.tag + "%",
						},
						callback: load_suppliers,
					});
				} else if (args.supplier_group) {
					frappe.db
						.get_list("Supplier", {
							filters: {
								supplier_group: args.supplier_group,
								disabled: 0,
							},
							limit: 100,
							order_by: "name",
						})
						.then((r) => {
							load_suppliers({ message: r });
						});
				}
			},
		});

		dialog.show();
	}
};

frappe.ui.form.set_controller("Request for Quotation", erpnext.buying.RequestforQuotationController);
