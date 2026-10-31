import { MACHINES, isPack } from "./machines";

const STORE_W = 330;
export const YC = 185;
const PROC_W = 230;
const PACK_W = 320;

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

function station(s, i, x) {
	const pack = isPack(s);
	const w = pack ? PACK_W : PROC_W;
	const half = MACHINES[s.machine]?.half ?? 50;
	const zone = pack ? { x, y: 20, w, h: 330 } : { x, y: YC - 150, w, h: 300 };
	const cx = x + w / 2;
	return {
		i,
		stage: s,
		pack,
		zone,
		x: cx,
		y: YC,
		inX: pack ? x + 16 : cx - half,
		outX: pack ? x + w : cx + half,
	};
}

function storePipes(items, M, color) {
	const out = [];
	const rows = {};
	items.filter((it) => it.shape !== "sacks").forEach((it) => (rows[it.rowY] ??= []).push(it));
	Object.values(rows).forEach((row) => {
		row.forEach((it) =>
			out.push({ x1: it.x, y1: it.y - it.r, x2: it.x, y2: it.rowY, flow: 0, color: it.m.color })
		);
		out.push({
			x1: Math.min(...row.map((it) => it.x)),
			y1: row[0].rowY,
			x2: M,
			y2: row[0].rowY,
			flow: 0,
			color: row[0].m.color,
		});
	});
	const ys = Object.keys(rows).map(Number);
	const above = ys.filter((y) => y < YC);
	const below = ys.filter((y) => y > YC);
	if (above.length) out.push({ x1: M, y1: Math.min(...above), x2: M, y2: YC, flow: 0, color });
	if (below.length) out.push({ x1: M, y1: Math.max(...below), x2: M, y2: YC, flow: 0, color });
	return out;
}

export function buildLayout(plant) {
	const items = storeItems(plant);
	const rows = Math.max(1, Math.ceil(items.length / 2));
	const H = Math.max(600, rows * 180 + 80);
	let x = 20 + STORE_W + 30;
	const stations = plant.stages.map((s, i) => {
		const st = station(s, i, x);
		x += st.zone.w + 20;
		return st;
	});
	const color = plant.product.color;
	const M = 20 + STORE_W - 12;
	const pipes = stations.length ? storePipes(items, M, color) : [];
	if (stations.length) pipes.push({ x1: M, y1: YC, x2: stations[0].inX, y2: YC, flow: 0, color });
	stations
		.slice(1)
		.forEach((st, k) =>
			pipes.push({ x1: stations[k].outX, y1: YC, x2: st.inX, y2: YC, flow: st.i, color })
		);
	const pack = stations.find((s) => s.pack);
	const fg = pack ? { x: pack.zone.x, y: 380, w: PACK_W, h: H - 400 } : null;
	return { W: x, H, store: { items, zone: { x: 20, y: 20, w: STORE_W, h: H - 40 } }, stations, pipes, fg };
}
