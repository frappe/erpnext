frappe.provide('erpnext.stock');

const CHART_COLORS = {
	red: 'rgb(255, 99, 132)',
	yellow: 'rgb(255, 205, 86)',
	blue: 'rgb(54, 162, 235)',
	orange: 'rgb(255, 159, 64)',
	green: 'rgb(75, 192, 192)',
	purple: 'rgb(153, 102, 255)',
	grey: 'rgb(201, 203, 207)'
};

erpnext.stock.ItemDashboard = Class.extend({
	init: function (opts) {
		$.extend(this, opts);
		this.make();
	},
	make: function () {
		var me = this;
		this.start = 0;
		if (!this.sort_by) {
			this.sort_by = 'projected_qty';
			// this.sort_by = 'actual_qty';
			this.sort_order = 'desc';
		}

		this.content = $(frappe.render_template('item_dashboard')).appendTo(this.parent);
		this.result = this.content.find('.result');

		this.content.on('click', '.btn-move', function () {
			handle_move_add($(this), "Move");
		});

		this.content.on('click', '.btn-add', function () {
			handle_move_add($(this), "Add");
		});

		this.content.on('click', '.btn-edit', function () {
			let item = unescape($(this).attr('data-item'));
			let warehouse = unescape($(this).attr('data-warehouse'));
			let company = unescape($(this).attr('data-company'));
			frappe.db.get_value('Putaway Rule', {
				'item_code': item,
				'warehouse': warehouse,
				'company': company
			}, 'name', (r) => {
				frappe.set_route("Form", "Putaway Rule", r.name);
			});
		});

		this.content.on('click', '.pending-breakdown', function() {
			let item_code = unescape($(this).attr('data-item'));
			let warehouse = unescape($(this).attr('data-warehouse'));

			if ($(`#pending-breakdown-${item_code}`).length){
				toggle_display(item_code, true);
			} else {
				let poi_results = get_coming_stocks(item_code, warehouse);
				let boi_results = get_reserved_stocks(item_code);
				append_breakdown($(this), item_code, poi_results, boi_results);
			}
		});

		this.content.on('click', '.to-collapse', function() {
			let item = unescape($(this).attr('data-item'));
			// let warehouse = unescape($(this).attr('data-warehouse'));
			// handle_breakdown($(this), item, warehouse);

			if ($(`#pending-breakdown-${item}`).length){
				toggle_display(item, false);
			} else {
				frappe.show_alert("Nothing to collapse")
			}
		});

		function toggle_display(item, display) {
			if (display) {
				$(`#pending-breakdown-${item}`).removeClass('hide');
			} else {
				$(`#pending-breakdown-${item}`).addClass('hide');
			}
		}


		function handle_move_add(element, action) {
			let item = unescape(element.attr('data-item'));
			let warehouse = unescape(element.attr('data-warehouse'));
			let actual_qty = unescape(element.attr('data-actual_qty'));
			let disable_quick_entry = Number(unescape(element.attr('data-disable_quick_entry')));
			let entry_type = action === "Move" ? "Material Transfer" : null;

			if (disable_quick_entry) {
				open_stock_entry(item, warehouse, entry_type);
			} else {
				if (action === "Add") {
					let rate = unescape($(this).attr('data-rate'));
					erpnext.stock.move_item(item, null, warehouse, actual_qty, rate, function () {
						me.refresh();
					});
				} else {
					erpnext.stock.move_item(item, warehouse, null, actual_qty, null, function () {
						me.refresh();
					});
				}
			}
		}

		function open_stock_entry(item, warehouse, entry_type) {
			frappe.model.with_doctype('Stock Entry', function () {
				var doc = frappe.model.get_new_doc('Stock Entry');
				if (entry_type) doc.stock_entry_type = entry_type;

				var row = frappe.model.add_child(doc, 'items');
				row.item_code = item;
				row.s_warehouse = warehouse;

				frappe.set_route('Form', doc.doctype, doc.name);
			});
		}

		// more
		this.content.find('.btn-more').on('click', function () {
			me.start += me.page_length;
			me.refresh();
		});

	},
	refresh: function () {
		if (this.before_refresh) {
			this.before_refresh();
		}

		let args = {
			item_code: this.item_code,
			warehouse: this.warehouse,
			parent_warehouse: this.parent_warehouse,
			item_group: this.item_group,
			company: this.company,
			start: this.start,
			sort_by: this.sort_by,
			sort_order: this.sort_order
		};

		var me = this;
		frappe.call({
			method: this.method,
			args: args,
			callback: function (r) {
				me.render(r.message);
			}
		});
	},
	render: function (data) {
		if (this.start === 0) {
			this.max_count = 0;
			this.result.empty();
		}

		let context = "";
		if (this.page_name === "warehouse-capacity-summary") {
			context = this.get_capacity_dashboard_data(data);
		} else {
			context = this.get_item_dashboard_data(data, this.max_count, true);
		}

		this.max_count = this.max_count;

		// show more button
		if (data && data.length === (this.page_length + 1)) {
			this.content.find('.more').removeClass('hidden');

			// remove the last element
			data.splice(-1);
		} else {
			this.content.find('.more').addClass('hidden');
		}

		// If not any stock in any warehouses provide a message to end user
		if (context.data.length > 0) {
			this.content.find('.result').css('text-align', 'unset');
			$(frappe.render_template(this.template, context)).appendTo(this.result);
		} else {
			var message = __("No Stock Available Currently");
			this.content.find('.result').css('text-align', 'center');

			$(`<div class='text-muted' style='margin: 20px 5px;'>
				${message} </div>`).appendTo(this.result);
		}
	},

	get_item_dashboard_data: function (data, max_count, show_item) {
		if (!max_count) max_count = 0;
		if (!data) data = [];

		data.forEach(function (d) {
			d.actual_or_pending = d.projected_qty + d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract;
			d.pending_qty = 0;
			d.total_reserved = d.reserved_qty + d.reserved_qty_for_production + d.reserved_qty_for_sub_contract;
			if (d.actual_or_pending > d.actual_qty) {
				d.pending_qty = d.actual_or_pending - d.actual_qty;
			}

			max_count = Math.max(d.actual_or_pending, d.actual_qty,
				d.total_reserved, max_count);
		});

		let can_write = 0;
		if (frappe.boot.user.can_write.indexOf("Stock Entry") >= 0) {
			can_write = 1;
		}

		return {
			data: data,
			max_count: max_count,
			can_write: can_write,
			show_item: show_item || false
		};
	},

	get_capacity_dashboard_data: function (data) {
		if (!data) data = [];

		data.forEach(function (d) {
			d.color = d.percent_occupied >= 80 ? "#f8814f" : "#2490ef";
		});

		let can_write = 0;
		if (frappe.boot.user.can_write.indexOf("Putaway Rule") >= 0) {
			can_write = 1;
		}

		return {
			data: data,
			can_write: can_write,
		};
	}
});

erpnext.stock.move_item = function (item, source, target, actual_qty, rate, callback) {
	var dialog = new frappe.ui.Dialog({
		title: target ? __('Add Item') : __('Move Item'),
		fields: [{
			fieldname: 'item_code',
			label: __('Item'),
			fieldtype: 'Link',
			options: 'Item',
			read_only: 1
		},
		{
			fieldname: 'source',
			label: __('Source Warehouse'),
			fieldtype: 'Link',
			options: 'Warehouse',
			read_only: 1
		},
		{
			fieldname: 'target',
			label: __('Target Warehouse'),
			fieldtype: 'Link',
			options: 'Warehouse',
			reqd: 1
		},
		{
			fieldname: 'qty',
			label: __('Quantity'),
			reqd: 1,
			fieldtype: 'Float',
			description: __('Available {0}', [actual_qty])
		},
		{
			fieldname: 'rate',
			label: __('Rate'),
			fieldtype: 'Currency',
			hidden: 1
		},
		],
	});
	dialog.show();
	dialog.get_field('item_code').set_input(item);

	if (source) {
		dialog.get_field('source').set_input(source);
	} else {
		dialog.get_field('source').df.hidden = 1;
		dialog.get_field('source').refresh();
	}

	if (rate) {
		dialog.get_field('rate').set_value(rate);
		dialog.get_field('rate').df.hidden = 0;
		dialog.get_field('rate').refresh();
	}

	if (target) {
		dialog.get_field('target').df.read_only = 1;
		dialog.get_field('target').value = target;
		dialog.get_field('target').refresh();
	}

	dialog.set_primary_action(__('Submit'), function () {
		var values = dialog.get_values();
		if (!values) {
			return;
		}
		if (source && values.qty > actual_qty) {
			frappe.msgprint(__('Quantity must be less than or equal to {0}', [actual_qty]));
			return;
		}
		if (values.source === values.target) {
			frappe.msgprint(__('Source and target warehouse must be different'));
		}

		frappe.call({
			method: 'erpnext.stock.doctype.stock_entry.stock_entry_utils.make_stock_entry',
			args: values,
			btn: dialog.get_primary_btn(),
			freeze: true,
			freeze_message: __('Creating Stock Entry'),
			callback: function (r) {
				frappe.show_alert(__('Stock Entry {0} created',
					['<a href="/app/stock-entry/' + r.message.name + '">' + r.message.name + '</a>']));
				dialog.hide();
				callback(r);
			},
		});
	});

	$('<p style="margin-left: 10px;"><a class="link-open text-muted small">' +
			__("Add more items or open full form") + '</a></p>')
		.appendTo(dialog.body)
		.find('.link-open')
		.on('click', function () {
			frappe.model.with_doctype('Stock Entry', function () {
				var doc = frappe.model.get_new_doc('Stock Entry');
				doc.from_warehouse = dialog.get_value('source');
				doc.to_warehouse = dialog.get_value('target');
				var row = frappe.model.add_child(doc, 'items');
				row.item_code = dialog.get_value('item_code');
				row.f_warehouse = dialog.get_value('target');
				row.t_warehouse = dialog.get_value('target');
				row.qty = dialog.get_value('qty');
				row.conversion_factor = 1;
				row.transfer_qty = dialog.get_value('qty');
				row.basic_rate = dialog.get_value('rate');
				frappe.set_route('Form', doc.doctype, doc.name);
			});
		});
}


function get_coming_stocks(item_code, warehouse) {
	let result = "";
	frappe.call({
		method: "fxnmrnth.fxnmrnth.report.backorder_summary.backorder_summary.get_qty",
		args: {
			item_code: item_code,
			warehouse: warehouse,
		},
		async: false,
		callback: (r) => {
			if (!r.exc) {
				result = r.message;
			} else {
				frappe.show_alert(`Error happened: ${r.exc}`)
			}
		}
	})
	return result
}

function get_reserved_stocks(item_code, warehouse) {
	let result = "";
	frappe.call({
		method: "fxnmrnth.fxnmrnth.report.backorder_analytics.backorder_analytics.get_bo_qty",
		args: {
			item_code: item_code,
		},
		async: false,
		callback: (r) => {
			if (!r.exc) {
				result = r.message;
			} else {
				frappe.show_alert(`Error happened: ${r.exc}`)
			}
		}
	})
	return result
}

function append_breakdown(element, item_code, poi_results, boi_results) {
	const $row = $(element).parents(`div[parent="${item_code}"]`)

	// Parse poi_results
	const poi_number_data = poi_results.map(r=> (r.qty-r.received_qty) )
	const poi_total_number =  poi_results.reduce( (total, r)=>{
		return total + (r.qty-r.received_qty)
	}, 0)
	const poi_label_data = poi_results.map(r=> `${r.parent} | ETA:${r.schedule_date}`)
	const poi_backgroundColor = []
	for (let i = 0; i < poi_results.length; i++) {
		const colorIndex = i % Object.keys(CHART_COLORS).length;
		poi_backgroundColor.push(Object.values(CHART_COLORS)[colorIndex])
	}

	// Setup poi chart
	let po_dataset_label = "Purchase Order"
	let po_options = {
		responsive: true,
		maintainAspectRatio: false,
		plugins: {
			legend: {
				position: "bottom",
				display: (poi_results.length >= 10) ? false : true,
				align: "start",

			},
			title: {
				display: true,
				text: `Total ${poi_total_number} ${po_dataset_label} Breakdown`
			}
		},
		// events: ['mousemove', 'mouseout', 'click'],
	}
	const po_config = setup(poi_number_data, poi_label_data, poi_backgroundColor, po_dataset_label, po_options);

	// Parse boi_results
	const boi_number_data = boi_results.map( r=> r.qty )

	// const boi_label_data = boi_results.map( r=> `${r.parent} | ${(r.customer_name)? (r.customer_name): "Customer Name Unset!"} | ${r.added_time} | Stock Required: {}`)

	const boi_total_number =  boi_results.reduce((total, r)=>{
		return total + r.qty
	}, 0)
	const boi_backgroundColor = []
	const boi_label_data = []
	var stockRequired = 0
	for (let i = 0; i < boi_results.length; i++) {
		const colorIndex = (i+5) % Object.keys(CHART_COLORS).length;
		boi_backgroundColor.push(Object.values(CHART_COLORS)[colorIndex])

		stockRequired += boi_results[i].qty
		let message = `${boi_results[i].parent} | ${(boi_results[i].customer_name)? (boi_results[i].customer_name): "Customer Name Unset!"} | ${boi_results[i].added_time} | Stock Required: ${stockRequired} | BO Qty ${boi_results[i].qty}`
		message += ` | Customer ID:${boi_results[i].customer_id}`
		let message2 = message.split(` | `)
		boi_label_data.push(message2)

	}


	// Setup boi chart
	let bo_dataset_label = "Backorder"
	let bo_options = {
		responsive: true,
		maintainAspectRatio: false,
		plugins: {
			legend: {
				position: "bottom",
				display: false,
				align: "start",
			},
			title: {
				display: true,
				text: `Total ${boi_total_number} ${bo_dataset_label} Breakdown`
			}
		},
	}
	const bo_config = setup(boi_number_data, boi_label_data, boi_backgroundColor, bo_dataset_label, bo_options);

	let Button = ""
	if (boi_results.length != 0){
		Button = `<div style="text-align: center">
		<button id="backorder-report" class="btn btn-primary" style="margin-top:20px">Open Backorder Analytics for this item.</button> 
		</div>`
	}
	// Add div for canvas
	let chartDisplay = `<div id="pending-breakdown-${item_code}" width="100%" class="col-sm-12" style="padding: 15px 15px;
		border-top: 1px solid #d1d8dd; border-left: 6px solid deepskyblue;">
		<div class="col-sm-6" style="width:48%; display:inline-block;">
			<canvas id="bo-${item_code}"></canvas>
		</div>
		<div class="col-sm-6" style="width:48%; display:inline-block;">
			<canvas id="po-${item_code}"></canvas>
		</div>
		${Button}

	</div>`

	let empty_display = `<div id="pending-breakdown-${item_code}" width="100%" class="col-sm-12" style="padding: 15px 15px;
		border-top: 1px solid #d1d8dd; border-left: 6px solid deepskyblue;">
		<h2> Seems like there's nothing to display. </h2>
		<h2> No stocks coming and no reserved quantity for any customers! </h2>
	</div>`

	if (poi_results.length > 0 || boi_results.length > 0) {
		$row.append(chartDisplay)
	} else {
		$row.append(empty_display)
	}
	$("#backorder-report" ).click(function() {
		window.location = '/desk#query-report/Backorder Analytics?item_code='+item_code;
	});
	// Render the chart using our configuration
	$.getScript("https://cdn.jsdelivr.net/npm/chart.js").done(function(){
		if (poi_results.length > 0){
			let po_ctx = document.getElementById(`po-${item_code}`);
			let poChart = new Chart(po_ctx, po_config);
	
			// Open a new tab for purchase order review
			po_ctx.onclick = function(evt){   
				var activePoints = poChart.getActiveElements(evt);
				if(activePoints.length > 0){
					//get the internal index of slice in pie chart
					var clickedElementindex = activePoints[0]["index"];
	
					//get specific label by index 
					var label = poChart.data.labels[clickedElementindex];
					let po_id  = label.split(" | ")[0]
					window.open(frappe.urllib.get_full_url(`/desk#Form/Purchase%20Order/${po_id}`));
	
					//get value by index      
					var value = poChart.data.datasets[0].data[clickedElementindex];
				}
			}
		}

		if (boi_results.length > 0){
			let bo_ctx = document.getElementById(`bo-${item_code}`);
			let boChart = new Chart(
				bo_ctx,
				bo_config
			);

			// Open a new tab for backorder review
			bo_ctx.onclick = function(evt){  
				var activePoints = boChart.getActiveElements(evt);
				if(activePoints.length > 0){
					//get the internal index of slice in pie chart
					var clickedElementindex = activePoints[0]["index"];

					//get specific label by index 
					var label = boChart.data.labels[clickedElementindex];
					let bo_id  = label[0]
					window.open(frappe.urllib.get_full_url(`/desk#Form/Backorder/${bo_id}`));

					//get value by index      
					var value = boChart.data.datasets[0].data[clickedElementindex];
				}
			}
		}
	});
}

// Setup for Purchase Order Item chart
function setup(number_data, label_data, backgroundColor, dataset_label, options) {
	const data = {
		labels: label_data,
		datasets: [{
			label: dataset_label,
			data: number_data,
			backgroundColor: backgroundColor,
			hoverOffset: 4
		}]
		};
	const config = {
		type: 'doughnut',
		data,
		options: options,
	};
	return config
}