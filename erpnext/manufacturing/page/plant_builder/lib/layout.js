import { isPackingModel, machineSize } from "./machines";

const STORE_W = 330;
export const YC = 185;
const PROC_W = 230;
const PACK_W = 320;
const ZONE_H = 300;
const ROW_H = ZONE_H + 20;
const LANE_Y = 27;

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

function station(s, i, x, row) {
	const pack = isPackingModel(s.machine_model);
	const w = pack ? PACK_W : PROC_W;
	const { half } = machineSize(s);
	const y = YC + row * ROW_H;
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

function feedPipes(fed, M, color) {
	const later = fed.filter((st) => st.column > 0);
	const out = fed
		.filter((st) => st.column === 0)
		.map((st) => ({ x1: M, y1: st.y, x2: st.inX, y2: st.y, flow: [st.i], color }));
	if (!later.length) return out;

	const flow = later.map((st) => st.i);
	out.push({ x1: M, y1: LANE_Y, x2: Math.max(...later.map((st) => st.x)), y2: LANE_Y, flow, color });
	later.forEach((st) =>
		out.push({ x1: st.x, y1: LANE_Y, x2: st.x, y2: st.y - st.half, flow: [st.i], color })
	);
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

export function buildLayout(plant) {
	const items = storeItems(plant);
	const groups = sequenceColumns(plant.stages);
	const deepest = Math.max(1, ...groups.map((group) => group.length));
	const H = Math.max(600, Math.ceil(items.length / 2) * 180 + 80, YC - ZONE_H / 2 + deepest * ROW_H);
	let x = 20 + STORE_W + 30;
	const columns = groups.map((group, column) => {
		const list = group.map((i, row) => ({ ...station(plant.stages[i], i, x, row), column }));
		x += Math.max(...list.map((st) => st.zone.w)) + 20;
		return list;
	});
	const stations = columns.flat().sort((a, b) => a.i - b.i);
	const color = plant.product.color;
	const M = 20 + STORE_W - 12;
	const fedStages = new Set(plant.materials.map((m) => m.stage));
	const fed = stations.filter((st) => fedStages.has(st.i + 1) || (st.column === 0 && !st.pack));
	const targets = fed.map((st) => (st.column === 0 ? st.y : LANE_Y));
	const pipes = stations.length
		? [
				...storePipes(
					items,
					M,
					targets,
					fed.map((st) => st.i),
					color
				),
				...feedPipes(fed, M, color),
		  ]
		: [];
	columns
		.slice(1)
		.forEach((list, k) =>
			list.forEach((to) => columns[k].forEach((from) => pipes.push(...route(from, to, color))))
		);
	const pack = stations.find((s) => s.pack);
	const fg = pack ? { x: pack.zone.x, y: 380, w: PACK_W, h: H - 400 } : null;
	return { W: x, H, store: { items, zone: { x: 20, y: 20, w: STORE_W, h: H - 40 } }, stations, pipes, fg };
}
