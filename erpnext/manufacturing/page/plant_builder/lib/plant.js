import { MATERIAL_TONES, machineKey, toneFor } from "./machines";
import { num } from "./format";

export const balancePercentage = (doc) =>
	100 -
	(doc.materials || []).filter((m) => !m.is_balance_item).reduce((sum, m) => sum + num(m.percentage), 0);

const percentageOf = (doc, row) => (row.is_balance_item ? balancePercentage(doc) : num(row.percentage));

export function newPlantDoc() {
	return {
		floor_name: "",
		company: window.frappe.defaults.get_default("company"),
		production_item: "",
		batch_size: 1000,
		formula_tolerance: 2,
		warehouse: "",
		fg_warehouse: "",
		materials: [],
		stages: [],
		packing_materials: [],
	};
}

export function toScenePlant(doc, machines, item) {
	const stages = (doc.stages || []).map((s, i) => ({
		id: s.name || `stage-${i}`,
		machine: machineKey(machines[s.workstation]?.machine_model || s.machine_model),
		shapes: machines[s.workstation]?.shapes || [],
		name: s.stage_name,
		output: s.semi_finished_good || "",
		packaging: (doc.packing_materials || []).map((p) => p.item_name || p.item_code),
		sequence: num(s.sequence_id),
	}));
	return {
		id: doc.name || "new",
		name: doc.floor_name,
		product: {
			name: item?.item_name || doc.production_item || "",
			unit: item?.stock_uom || "Unit",
			fillKg: num(item?.weight_per_unit),
			color: toneFor(doc.production_item),
		},
		materials: (doc.materials || []).map((m, i) => ({
			id: m.item_code || `material-${i}`,
			name: m.item_name || m.item_code || "",
			pct: percentageOf(doc, m),
			balance: !!m.is_balance_item,
			storage: m.storage,
			stage: num(m.stage_row_id) || 1,
			color: MATERIAL_TONES[i % MATERIAL_TONES.length],
		})),
		stages,
	};
}

export const runsWithStageAbove = (stages, i) =>
	i > 0 && num(stages[i].sequence_id) > 0 && stages[i].sequence_id === stages[i - 1].sequence_id;

function setSequences(stages, parallel) {
	let sequence = 0;
	stages.forEach((stage, i) => (stage.sequence_id = i > 0 && parallel[i] ? sequence : ++sequence));
}

function changeStages(doc, change, stageOf) {
	const parallel = doc.stages.map((_, i) => runsWithStageAbove(doc.stages, i));
	change(doc.stages, parallel);
	(doc.materials || []).forEach((row) => (row.stage_row_id = stageOf(num(row.stage_row_id) || 1)));
	setSequences(doc.stages, parallel);
}

export function setRunsWithStageAbove(doc, index, value) {
	changeStages(
		doc,
		(_, parallel) => (parallel[index] = value),
		(no) => no
	);
}

export function moveStage(doc, from, to) {
	const order = doc.stages.map((_, i) => i + 1);
	const move = (list) => list.splice(to, 0, ...list.splice(from, 1));
	changeStages(
		doc,
		(stages, parallel) => [stages, parallel, order].forEach(move),
		(no) => order.indexOf(no) + 1
	);
}

export function insertStage(doc, index, stage) {
	changeStages(
		doc,
		(stages, parallel) => (stages.splice(index, 0, stage), parallel.splice(index, 0, false)),
		(no) => (no > index ? no + 1 : no)
	);
}

export function removeStage(doc, index) {
	changeStages(
		doc,
		(stages, parallel) => (stages.splice(index, 1), parallel.splice(index, 1)),
		(no) => (no === index + 1 ? 1 : no > index + 1 ? no - 1 : no)
	);
}
