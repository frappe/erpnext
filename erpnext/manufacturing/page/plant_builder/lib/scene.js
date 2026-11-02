import { MACHINES, machineSize } from "./machines";
import { YC } from "./layout";
import { fmt, plural } from "./format";

export function previewView(plant, animate, focus) {
	const level = {};
	plant.materials.forEach((m) => (level[`m:${m.id}`] = 75));
	plant.stages.forEach((_, i) => (level[`s${i}`] = animate ? 60 : 0));
	const all = (value) => plant.stages.map(() => value);
	return {
		level,
		mode: all(animate ? "run" : "off"),
		working: all(animate),
		flow: all(animate),
		active: plant.stages.map((_, i) => focus === i),
		storeActive: false,
		fgActive: false,
		cartons: animate ? 0.5 : 0,
		crates: 1,
	};
}

function stationTag(plant, station, view, holding) {
	const machine = MACHINES[station.stage.machine];
	const title = station.stage.name || machine.label;
	const active = view.active[station.i];
	const sub = holding ? holding(station.i) : machine.label;
	if (!station.pack) {
		return {
			id: `s${station.i}`,
			x: station.x,
			y: station.y,
			z: machineSize(station.stage).height + 12,
			title,
			sub,
			active,
		};
	}
	return { id: `s${station.i}`, x: station.zone.x + 205, y: YC - 30, z: 84, title, sub, active };
}

function storeTag(item, stock) {
	const key = `m:${item.m.id}`;
	const sacks = item.shape === "sacks";
	const sub = stock ? stock(item.m) : `${fmt(item.m.pct)}%`;
	return {
		id: key,
		x: item.x,
		y: sacks ? item.y + 30 : item.y,
		z: sacks ? 46 : item.h + 6,
		title: item.m.name || "",
		sub,
	};
}

export function buildTags(plant, layout, view, live = {}) {
	const tags = [
		...layout.store.items.map((item) => storeTag(item, live.stock)),
		...layout.stations.map((station) => stationTag(plant, station, view, live.holding)),
	];
	if (!layout.fg) return tags;

	const unit = plural(plant.product.unit).toLowerCase();
	const sub = live.packed !== undefined ? `${fmt(live.packed)} ${unit}` : plant.product.name || "";
	return [
		...tags,
		{
			id: "fg",
			x: layout.fg.x + 160,
			y: layout.fg.y + 105,
			z: 70,
			title: "Finished goods",
			sub,
			active: view.fgActive,
		},
	];
}
