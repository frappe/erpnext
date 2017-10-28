frappe.provide('agriculture');

agriculture.TernaryPlot = class TernaryPlot {
	constructor(opts) {
		Object.assign(this, opts);

		frappe.require('assets/frappe/js/lib/snap.svg-min.js', () => {
			this.make_svg();
			this.init_snap();
			this.init_config();
			this.make_plot();
			this.make_legends();
			this.mark_blip();
		});
	}

	make_svg() {
		this.$svg = $('<svg height="350" width="400">');
		$(this.parent).append(this.$svg);
	}

	init_snap() {
		this.paper = new Snap(this.$svg.get(0));
	}

	init_config() {
		this.config = {
			triangle_side: 300,
			spacing: 50,
			strokeWidth: 1,
			stroke: frappe.ui.color.get('black')
		};
		this.config.scaling_factor = this.config.triangle_side / 100;
		let { triangle_side: t, spacing: s, scaling_factor: p } = this.config;

		this.coords = {
			sand: {
				points: [
					s + t * Snap.cos(60), s,
					s, s + t * Snap.cos(30),
					s + t, s + t * Snap.cos(30)
				],
				color: frappe.ui.color.get('peach')
			},
			loamy_sand: {
				points: [
					s + 15 * p * Snap.cos(60), s + (100 - 15) * p * Snap.cos(30),
					s + 10 * p * Snap.cos(60), s + (100 - 10) * p * Snap.cos(30),
					s + (100 - 85) * p, s + t * Snap.cos(30),
					s + (100 - 70) * p, s + t * Snap.cos(30)
				],
				color: frappe.ui.color.get('pink')
			},
			sandy_loam: {
				points: [
					s + 20 * p * Snap.cos(60) + 27.5 * p, s + (100 - 20) * p * Snap.cos(30),
					s + 20 * p * Snap.cos(60), s + (100 - 20) * p * Snap.cos(30),
					s + 15 * p * Snap.cos(60), s + (100 - 15) * p * Snap.cos(30),
					s + (100 - 75) * p, s + t * Snap.cos(30),
					s + (100 - 50) * p, s + t * Snap.cos(30),
					s + (100 - 50) * p + 7.5 * p * Snap.cos(60), s + t * Snap.cos(30) - 7.5 * p * Snap.cos(30),
					s + (100 - 50) * p + 7.5 * p * Snap.cos(60) - 10 * p, s + t * Snap.cos(30) - 7.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('pink', 'light')
			},
			loam: {
				points: [
					s + (100 - 50) * p + 27.5 * p * Snap.cos(60), s + t * Snap.cos(30) - 27.5 * p * Snap.cos(30),
					s + (100 - 50) * p + 27.5 * p * Snap.cos(60) - 22.5 * p, s + t * Snap.cos(30) - 27.5 * p * Snap.cos(30),
					s + 20 * p * Snap.cos(60) + 27.5 * p, s + (100 - 20) * p * Snap.cos(30),
					s + (100 - 50) * p + 7.5 * p * Snap.cos(60) - 10 * p, s + t * Snap.cos(30) - 7.5 * p * Snap.cos(30),
					s + (100 - 50) * p + 7.5 * p * Snap.cos(60), s + t * Snap.cos(30) - 7.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('brown')
			},
			silt_loam: {
				points: [
					s + t - 27.5 * p * Snap.cos(60), s + 72.5 * p * Snap.cos(30),
					s + (100 - 50) * p + 27.5 * p * Snap.cos(60), s + t * Snap.cos(30) - 27.5 * p * Snap.cos(30),
					s + (100 - 50) * p, s + t * Snap.cos(30),
					s + (100 - 20) * p, s + t * Snap.cos(30),
					s + (100 - 20) * p + 12.5 * p * Snap.cos(60), s + 90 * p * Snap.cos(30),
					s + t - 12.5 * p * Snap.cos(60), s + (100 - 12.5) * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('green', 'dark')
			},
			silt: {
				points: [
					s + t - 12.5 * p * Snap.cos(60), s + (100 - 12.5) * p * Snap.cos(30),
					s + (100 - 20) * p + 12.5 * p * Snap.cos(60), s + 90 * p * Snap.cos(30),
					s + (100 - 20) * p, s + t * Snap.cos(30),
					s + t, s + t * Snap.cos(30)
				],
				color: frappe.ui.color.get('green')
			},
			silty_clay_loam: {
				points: [
					s + t - 40 * p * Snap.cos(60), s + 60 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 20 * p, s + 60 * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60) - 20 * p, s + 72.5 * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60), s + 72.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('cyan', 'dark')
			},
			silty_clay: {
				points: [
					s + t - 60 * p * Snap.cos(60), s + 40 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 20 * p, s + 60 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60), s + 60 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('cyan')
			},
			clay_loam: {
				points: [
					s + t - 40 * p * Snap.cos(60) - 20 * p, s + 60 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 45 * p, s + 60 * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60) - 45 * p, s + 72.5 * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60) - 20 * p, s + 72.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('green', 'light')
			},
			sandy_clay_loam: {
				points: [
					s + 35 * p * Snap.cos(60) + 20 * p, s + (100 - 35) * p * Snap.cos(30),
					s + 35 * p * Snap.cos(60), s + (100 - 35) * p * Snap.cos(30),
					s + 20 * p * Snap.cos(60), s + (100 - 20) * p * Snap.cos(30),
					s + 20 * p * Snap.cos(60) + 27.5 * p, s + (100 - 20) * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60) - 45 * p, s + 72.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('pink', 'dark')
			},
			sandy_clay: {
				points: [
					s + 55 * p * Snap.cos(60), s + (100 - 55) * p * Snap.cos(30),
					s + 35 * p * Snap.cos(60), s + (100 - 35) * p * Snap.cos(30),
					s + 35 * p * Snap.cos(60) + 20 * p, s + (100 - 35) * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('red')
			},
			clay: {
				points: [
					s + t * Snap.cos(60), s,
					s + 55 * p * Snap.cos(60), s + (100 - 55) * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 45 * p, s + 60 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 20 * p, s + 60 * p * Snap.cos(30),
					s + t - 60 * p * Snap.cos(60), s + 40 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('yellow')
			},
		};
	}

	get_coords(soil_type) {
		return this.coords[soil_type].points;
	}

	get_color(soil_type) {
		return this.coords[soil_type].color;
	}

	make_plot() {
		for (let soil_type in this.coords) {
			this.paper.polygon(this.get_coords(soil_type)).attr({
				fill: this.get_color(soil_type),
				stroke: this.config.stroke,
				strokeWidth: this.config.strokeWidth
			});
		}
	}

	make_legends() {
		let { triangle_side: t, spacing: s, scaling_factor: p } = this.config;

		let clay = this.paper.text(t * Snap.cos(60) / 2, s + t * Snap.cos(30) / 2, "Clay").attr({
			fill: "black"
		});
		clay.transform("r300");

		let silt = this.paper.text(t, s + t * Snap.cos(30) / 2, "Silt").attr({
			fill: "black"
		});
		silt.transform("r60");

		let sand = this.paper.text(35 + t * Snap.cos(60), 90 + t * Snap.cos(30), "Sand").attr({
			fill: "black"
		});
		sand.transform("r0");
	}

	mark_blip({clay, sand, silt} = this) {
		let { triangle_side: t, spacing: s, scaling_factor: p } = this.config;

		let x_blip = s + clay * p * Snap.cos(60) + silt * p;
		let y_blip = s + silt * p * Snap.cos(30) + sand * p * Snap.sin(60);

		this.paper.circle(x_blip, y_blip, 4).attr({
			fill: frappe.ui.color.get("orange"),
			stroke: frappe.ui.color.get("orange"),
			strokeWidth: 2
		});
	}
};