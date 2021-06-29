erpnext.HierarchyChart = class {

	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = wrapper.page;

		this.page.main.css({
			'min-height': '300px',
			'max-height': '600px',
			'overflow': 'auto',
			'position': 'relative'
		});
		this.page.main.addClass('frappe-card');

		this.nodes = {};
		this.setup_node_class();
	}

	setup_node_class() {
		let me = this;
		this.Node = class {
			constructor({
				id, parent, parent_id, image, name, title, expandable, connections, is_root // eslint-disable-line
			}) {
				// to setup values passed via constructor
				$.extend(this, arguments[0]);

				this.expanded = 0;

				me.nodes[this.id] = this;
				me.make_node_element(this);
				me.setup_node_click_action(this);
			}
		}
	}

	make_node_element(node) {
		let node_card = frappe.render_template('node_card', {
			id: node.id,
			name: node.name,
			title: node.title,
			image: node.image,
			parent: node.parent_id,
			connections: node.connections
		});

		node.parent.append(node_card);
		node.$link = $(`#${node.id}`);
	}

	show() {
		frappe.breadcrumbs.add('HR');

		let me = this;
		let company = this.page.add_field({
			fieldtype: 'Link',
			options: 'Company',
			fieldname: 'company',
			placeholder: __('Select Company'),
			default: frappe.defaults.get_default('company'),
			only_select: true,
			reqd: 1,
			change: () => {
				me.company = undefined;

				if (company.get_value() && me.company != company.get_value()) {
					me.company = company.get_value();

					// svg for connectors
					me.make_svg_markers()

					if (me.$hierarchy)
						me.$hierarchy.remove();

					// setup hierarchy
					me.$hierarchy = $(
						`<ul class="hierarchy">
							<li class="root-level level"></li>
						</ul>`);

					me.page.main.append(me.$hierarchy);
					me.render_root_node();
				}
			}
		});

		company.refresh();
		$(`[data-fieldname="company"]`).trigger('change');
	}

	make_svg_markers() {
		$('#arrows').remove();

		this.page.main.prepend(`
			<svg id="arrows" width="100%" height="100%">
				<defs>
					<marker id="arrowhead-active" viewBox="0 0 10 10" refX="3" refY="5" markerWidth="6" markerHeight="6" orient="auto" fill="var(--blue-500)">
						<path d="M 0 0 L 10 5 L 0 10 z"></path>
					</marker>
					<marker id="arrowhead-collapsed" viewBox="0 0 10 10" refX="3" refY="5" markerWidth="6" markerHeight="6" orient="auto" fill="var(--blue-300)">
						<path d="M 0 0 L 10 5 L 0 10 z"></path>
					</marker>

					<marker id="arrowstart-active" viewBox="0 0 10 10" refX="3" refY="5" markerWidth="8" markerHeight="8" orient="auto" fill="var(--blue-500)">
						<circle cx="4" cy="4" r="3.5" fill="white" stroke="var(--blue-500)"/>
					</marker>
					<marker id="arrowstart-collapsed" viewBox="0 0 10 10" refX="3" refY="5" markerWidth="8" markerHeight="8" orient="auto" fill="var(--blue-300)">
						<circle cx="4" cy="4" r="3.5" fill="white" stroke="var(--blue-300)"/>
					</marker>
				</defs>
				<g id="connectors" fill="none">
				</g>
			</svg>`);
	}

	render_root_node() {
		this.method = 'erpnext.hr.page.organizational_chart.organizational_chart.get_children';

		let me = this;

		frappe.call({
			method: me.method,
			args: {
				company: me.company
			},
			callback: function(r) {
				if (r.message.length) {
					let data = r.message[0];

					let root_node = new me.Node({
						id: data.name,
						parent: me.$hierarchy.find('.root-level'),
						parent_id: undefined,
						image: data.image,
						name: data.employee_name,
						title: data.designation,
						expandable: true,
						connections: data.connections,
						is_root: true,
					});

					me.expand_node(root_node);
				}
			}
		})
	}

	expand_node(node) {
		let is_sibling = this.selected_node && this.selected_node.parent_id === node.parent_id;
		this.set_selected_node(node);
		this.show_active_path(node);
		this.collapse_previous_level_nodes(node);

		// since the previous node collapses, all connections to that node need to be rebuilt
		// if a sibling node is clicked, connections don't need to be rebuilt
		if (!is_sibling) {
			// rebuild outgoing connections
			this.refresh_connectors(node.parent_id);

			// rebuild incoming connections
			let grandparent = $(`#${node.parent_id}`).attr('data-parent');
			this.refresh_connectors(grandparent)
		}

		if (node.expandable && !node.expanded) {
			return this.load_children(node);
		}
	}

	collapse_node() {
		if (this.selected_node.expandable) {
			this.selected_node.$children.hide();
			$(`path[data-parent="${this.selected_node.id}"]`).hide();
			this.selected_node.expanded = false;
		}
	}

	show_active_path(node) {
		// mark node parent on active path
		$(`#${node.parent_id}`).addClass('active-path');
	}

	load_children(node) {
		frappe.run_serially([
			() => this.get_child_nodes(node.id),
			(child_nodes) => this.render_child_nodes(node, child_nodes)
		]);
	}

	get_child_nodes(node_id) {
		let me = this;
		return new Promise(resolve => {
			frappe.call({
				method: this.method,
				args: {
					parent: node_id,
					company: me.company
				},
				callback: (r) => {
					resolve(r.message);
				}
			});
		});
	}

	render_child_nodes(node, child_nodes) {
		const last_level = this.$hierarchy.find('.level:last').index();
		const current_level = $(`#${node.id}`).parent().parent().parent().index();

		if (last_level === current_level) {
			this.$hierarchy.append(`
				<li class="level"></li>
			`);
		}

		if (!node.$children) {
			node.$children = $('<ul class="node-children"></ul>')
					.hide()
					.appendTo(this.$hierarchy.find('.level:last'));

			node.$children.empty();

			if (child_nodes) {
				$.each(child_nodes, (_i, data) => {
					this.add_node(node, data);

					setTimeout(() => {
						this.add_connector(node.id, data.name);
					}, 250);
				});
			}
		}

		node.$children.show();
		$(`path[data-parent="${node.id}"]`).show();
		node.expanded = true;
	}

	add_node(node, data) {
		var $li = $('<li class="child-node"></li>');

		return new this.Node({
			id: data.name,
			parent: $li.appendTo(node.$children),
			parent_id: node.id,
			image: data.image,
			name: data.employee_name,
			title: data.designation,
			expandable: data.expandable,
			connections: data.connections,
			children: undefined
		});
	}

	add_connector(parent_id, child_id) {
		let parent_node = document.querySelector(`#${parent_id}`);
		let child_node = document.querySelector(`#${child_id}`);

		// variable for the namespace
		const svgns = 'http://www.w3.org/2000/svg';
		let path = document.createElementNS(svgns, 'path');

		// we need to connect right side of the parent to the left side of the child node
		let pos_parent_right = {
			x: parent_node.offsetLeft + parent_node.offsetWidth,
			y: parent_node.offsetTop + parent_node.offsetHeight / 2
		};
		let pos_child_left = {
			x: child_node.offsetLeft - 5,
			y: child_node.offsetTop + child_node.offsetHeight / 2
		};

		let connector =
			"M" +
			(pos_parent_right.x) + "," + (pos_parent_right.y) + " " +
			"C" +
			(pos_parent_right.x + 100) + "," + (pos_parent_right.y) + " " +
			(pos_child_left.x - 100) + "," + (pos_child_left.y) + " " +
			(pos_child_left.x) + "," + (pos_child_left.y);

		path.setAttribute("d", connector);
		path.setAttribute("data-parent", parent_id);
		path.setAttribute("data-child", child_id);

		if ($(`#${parent_id}`).hasClass('active')) {
			path.setAttribute("class", "active-connector");
			path.setAttribute("marker-start", "url(#arrowstart-active)");
			path.setAttribute("marker-end", "url(#arrowhead-active)");
		} else if ($(`#${parent_id}`).hasClass('active-path')) {
			path.setAttribute("class", "collapsed-connector");
			path.setAttribute("marker-start", "url(#arrowstart-collapsed)");
			path.setAttribute("marker-end", "url(#arrowhead-collapsed)");
		}

		$('#connectors').append(path);
	}

	set_selected_node(node) {
		// remove .active class from the current node
		$('.active').removeClass('active');

		// add active class to the newly selected node
		this.selected_node = node;
		node.$link.addClass('active');
	}

	collapse_previous_level_nodes(node) {
		let node_parent = $(`#${node.parent_id}`);

		let previous_level_nodes = node_parent.parent().parent().children('li');
		if (node_parent.parent().hasClass('root-level')) {
			previous_level_nodes = node_parent.parent().children('li');
		}

		let node_card = undefined;

		previous_level_nodes.each(function() {
			node_card = $(this).find('.node-card');

			if (!node_card.hasClass('active-path')) {
				node_card.addClass('collapsed');
			}
		});
	}

	refresh_connectors(node_parent) {
		if (!node_parent) return;

		$(`path[data-parent="${node_parent}"]`).remove();

		frappe.run_serially([
			() => this.get_child_nodes(node_parent),
			(child_nodes) => {
				if (child_nodes) {
					$.each(child_nodes, (_i, data) => {
						this.add_connector(node_parent, data.name);
					});
				}
			}
		]);
	}

	setup_node_click_action(node) {
		let me = this;
		let node_element = $(`#${node.id}`);

		node_element.click(function() {
			let is_sibling = me.selected_node.parent_id === node.parent_id;

			if (is_sibling) {
				me.collapse_node();
			} else if (node_element.is(':visible')
				&& (node_element.hasClass('collapsed') || node_element.hasClass('active-path'))) {
				me.remove_levels_after_node(node);
				me.remove_orphaned_connectors();
			}

			me.expand_node(node);
		});
	}

	remove_levels_after_node(node) {
		let level = $(`#${node.id}`).parent().parent().parent();

		if ($(`#${node.id}`).parent().hasClass('root-level')) {
			level = $(`#${node.id}`).parent();
		}

		level = $('.hierarchy > li:eq('+ level.index() + ')');
		level.nextAll('li').remove();

		let nodes = level.find('.node-card');
		let node_object = undefined;

		$.each(nodes, (_i, element) => {
			node_object = this.nodes[element.id];
			node_object.expanded = 0;
			node_object.$children = undefined;
		});

		nodes.removeClass('collapsed active-path');
	}

	remove_orphaned_connectors() {
		let paths = $('#connectors > path');
		$.each(paths, (_i, path) => {
			let parent = $(path).data('parent');
			let child = $(path).data('child');

			if ($(parent).length || $(child).length)
				return;

			$(path).remove();
		})
	}
}