import { isPackingModel, machineSize } from "../../plant_builder/lib/machines";

const LABEL_WIDTH = 230;
const GAP = 24;
const ROW_HEIGHT = 300;
const ROW_GAP = 60;

function placeWorkstation(row, x, top) {
	const pack = isPackingModel(row.machine_model);
	const size = machineSize({ machine_model: row.machine_model, shapes: row.shapes });
	const w = pack ? 340 : Math.max(220, size.half * 2 + 90);
	const zone = { x, y: top, w, h: ROW_HEIGHT };
	return { row, zone, pack, x: x + w / 2, y: top + ROW_HEIGHT / 2, tagZ: (size.height || 100) + 16 };
}

export function buildLayout(lines) {
	let top = ROW_GAP;
	let width = 0;
	const rows = lines.map((line) => {
		let x = LABEL_WIDTH;
		const placed = line.workstations.map((row) => {
			const cell = placeWorkstation(row, x, top);
			x += cell.zone.w + GAP;
			return cell;
		});
		const result = {
			line,
			top,
			cells: placed,
			label: { x: 24, y: top + ROW_HEIGHT / 2 - 50, w: LABEL_WIDTH - 44 },
		};
		width = Math.max(width, x);
		top += ROW_HEIGHT + ROW_GAP;
		return result;
	});
	return { W: Math.max(width, 600), H: top, rows };
}
