import { isPackingModel, machineSize } from "./machines";

const STORE_W = 330;
export const YC = 185;
const PROC_W = 230;
const PACK_W = 320;
const ZONE_H = 300;
const ROW_H = ZONE_H + 20;
const LANE_Y = 27;
const MAX_PER_ROW = 3;
const BAND_GAP = 40;

function storeItems(plant) {
	return plant.materials.map((m, i) => {
		const shape = { Sacks: "sacks", Silo: "silo" }[m.storage] || "tank";
		const r = shape === "silo" ? 38 : 42;
		const h = shape === "silo" ? 150 : 120;
		const x = 20 + 90 + (i % 2) * 150;
		const y = 20 + 110 + Math.floor(i / 2) * 180;
		return { m, x, y, r, h, shape, rowY: y - 62 };
	});
}

function station(s, i, x, place) {
	const pack = isPackingModel(s.machine_model);
	const w = pack ? PACK_W : PROC_W;
	const { half } = machineSize(s);
	const y = YC + place.band * place.bandH + place.row * ROW_H;
	const zone = pack ? { x, y: 20, w, h: 330 } : { x, y: y - ZONE_H / 2, w, h: ZONE_H };
	const cx = x + w / 2;
	return {
		i,
		stage: s,
		pack,
		half,
		zone,
		x: cx,
		y,
		band: place.band,
		slot: place.slot,
		inX: pack ? x + 16 : cx - half,
		outX: pack ? x + w : cx + half,
	};
}

function sequenceColumns(stages) {
	const columns = new Map();
	stages.forEach((s, i) => columns.set(s.sequence, [...(columns.get(s.sequence) || []), i]));
	return [...columns.keys()].sort((a, b) => a - b).map((key) => columns.get(key));
}

function storePipes(items, M, targets, flow, color) {
	const out = [];
	const rows = {};
	items.filter((it) => it.shape !== "sacks").forEach((it) => (rows[it.rowY] ??= []).push(it));
	Object.values(rows).forEach((row) => {
		row.forEach((it) =>
			out.push({ x1: it.x, y1: it.y - it.r, x2: it.x, y2: it.rowY, flow, color: it.m.color })
		);
		const x1 = Math.min(...row.map((it) => it.x));
		out.push({ x1, y1: row[0].rowY, x2: M, y2: row[0].rowY, flow, color: row[0].m.color });
	});
	const ys = [...Object.keys(rows).map(Number), ...targets];
	if (Math.max(...ys) > Math.min(...ys)) {
		out.push({ x1: M, y1: Math.min(...ys), x2: M, y2: Math.max(...ys), flow, color });
	}
	return out;
}

function feedPipes(fed, M, laneOf, color) {
	const out = fed
		.filter((st) => st.slot === 0)
		.map((st) => ({ x1: M, y1: st.y, x2: st.inX, y2: st.y, flow: [st.i], color }));
	const lanes = new Map();
	fed.filter((st) => st.slot > 0).forEach((st) =>
		lanes.set(laneOf(st), [...(lanes.get(laneOf(st)) || []), st])
	);
	lanes.forEach((later, lane) => {
		const flow = later.map((st) => st.i);
		out.push({ x1: M, y1: lane, x2: Math.max(...later.map((st) => st.x)), y2: lane, flow, color });
		later.forEach((st) =>
			out.push({ x1: st.x, y1: lane, x2: st.x, y2: st.y - st.half, flow: [st.i], color })
		);
	});
	return out;
}

function route(from, to, color) {
	const flow = [to.i];
	if (from.y === to.y) return [{ x1: from.outX, y1: from.y, x2: to.inX, y2: to.y, flow, color }];
	const mx = Math.round((from.outX + to.inX) / 2);
	return [
		{ x1: from.outX, y1: from.y, x2: mx, y2: from.y, flow, color },
		{ x1: mx, y1: from.y, x2: mx, y2: to.y, flow, color },
		{ x1: mx, y1: to.y, x2: to.inX, y2: to.y, flow, color },
	];
}

function laneRoute(from, to, lane, color) {
	const flow = [to.i];
	const gx = from.zone.x + from.zone.w + 10;
	const endX = to.zone.x - (to.pack ? 10 : 15);
	const points = [
		[from.outX, from.y],
		[gx, from.y],
		[gx, lane],
		[endX, lane],
		[endX, to.y],
		[to.inX, to.y],
	];
	return points
		.slice(1)
		.map(([x2, y2], k) => ({ x1: points[k][0], y1: points[k][1], x2, y2, flow, color }));
}

function placeColumns(plant, groups, deepest) {
	const isPack = (group) => group.some((i) => isPackingModel(plant.stages[i].machine_model));
	const process = groups.filter((group) => !isPack(group)).length;
	const bands = Math.max(1, Math.ceil(process / MAX_PER_ROW));
	const perRow = Math.max(1, Math.ceil(process / bands));
	const bandH = deepest * ROW_H + BAND_GAP;
	const start = 20 + STORE_W + 30;
	const packX = start + perRow * (PROC_W + 20);
	const columns = groups.map((group, column) => {
		const pack = isPack(group);
		const band = pack ? 0 : Math.floor(column / perRow);
		const slot = pack ? 0 : column % perRow;
		const x = pack ? packX : start + slot * (PROC_W + 20);
		return group.map((i, row) => ({
			...station(plant.stages[i], i, x, { band, slot, row, bandH }),
			column,
		}));
	});
	const hasPack = groups.some(isPack);
	return { columns, bands, bandH, W: packX + (hasPack ? PACK_W + 20 : 0) };
}

export function buildLayout(plant) {
	const items = storeItems(plant);
	const groups = sequenceColumns(plant.stages);
	const deepest = Math.max(1, ...groups.map((group) => group.length));
	const { columns, bands, bandH, W } = placeColumns(plant, groups, deepest);
	const lastBottom = YC + (bands - 1) * bandH + (deepest - 1) * ROW_H + ZONE_H / 2;
	const H = Math.max(600, Math.ceil(items.length / 2) * 180 + 80, lastBottom + 20);
	const gapAbove = (band) => YC + band * bandH - ZONE_H / 2 - BAND_GAP / 2;
	const laneOf = (st) => (st.band ? gapAbove(st.band) : LANE_Y);
	const stations = columns.flat().sort((a, b) => a.i - b.i);
	const color = plant.product.color;
	const M = 20 + STORE_W - 12;
	const fedStages = new Set(plant.materials.map((m) => m.stage));
	const fed = stations.filter((st) => fedStages.has(st.i + 1) || (st.column === 0 && !st.pack));
	const targets = fed.map((st) => (st.slot === 0 ? st.y : laneOf(st)));
	const pipes = stations.length
		? [
				...storePipes(
					items,
					M,
					targets,
					fed.map((st) => st.i),
					color
				),
				...feedPipes(fed, M, laneOf, color),
		  ]
		: [];
	columns
		.slice(1)
		.forEach((list, k) =>
			list.forEach((to) =>
				columns[k].forEach((from) =>
					pipes.push(
						...(from.band === to.band
							? route(from, to, color)
							: laneRoute(from, to, gapAbove(Math.max(from.band, to.band)), color))
					)
				)
			)
		);
	const pack = stations.find((s) => s.pack);
	const fg = pack ? { x: pack.zone.x, y: 380, w: PACK_W, h: H - 400 } : null;
	return { W, H, store: { items, zone: { x: 20, y: 20, w: STORE_W, h: H - 40 } }, stations, pipes, fg };
}

export function buildFloorLayout(plant) {
	const count = plant.stages.length;
	const perRow = Math.max(1, Math.min(MAX_PER_ROW + 1, Math.ceil(Math.sqrt(count))));
	const stations = plant.stages.map((s, i) => {
		const slot = i % perRow;
		const row = Math.floor(i / perRow);
		const pack = isPackingModel(s.machine_model);
		const x = 20 + slot * (PACK_W + 20) + (pack ? 0 : (PACK_W - PROC_W) / 2);
		const st = station(s, i, x, { band: 0, slot, row, bandH: 0 });
		return pack ? { ...st, zone: { ...st.zone, y: st.y - ZONE_H / 2, h: ZONE_H } } : st;
	});
	const rows = Math.max(1, Math.ceil(count / perRow));
	return {
		W: 20 + Math.min(perRow, Math.max(count, 1)) * (PACK_W + 20),
		H: Math.max(400, YC + (rows - 1) * ROW_H + ZONE_H / 2 + 20),
		store: { items: [], zone: null },
		stations,
		pipes: [],
		fg: null,
	};
}
