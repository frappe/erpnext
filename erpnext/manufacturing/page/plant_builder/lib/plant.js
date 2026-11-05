import { MATERIAL_TONES, toneFor } from "./machines";
import { __ } from "./api";
import { num } from "./format";

export const machineModelOf = (stage, machines) =>
	machines[stage.workstation]?.machine_model || stage.machine_model;

export function toScenePlant(doc, machines, item) {
	const stages = (doc.stages || []).map((s, i) => ({
		id: s.name || `stage-${i}`,
		machine_model: machineModelOf(s, machines),
		shapes: machines[s.workstation]?.shapes || [],
		name: s.operation || s.stage_name,
		output: s.semi_finished_good || "",
		packaging: (doc.packing_materials || []).map((p) => p.item_name || p.item_code),
		sequence: num(s.sequence_id),
	}));
	return {
		id: doc.name || "new",
		name: doc.name || "",
		product: {
			name: item?.item_name || doc.production_item || "",
			unit: item?.stock_uom || __("Unit"),
			fillKg: num(item?.weight_per_unit),
			color: toneFor(doc.production_item),
		},
		materials: (doc.materials || []).map((m, i) => ({
			id: m.item_code || `material-${i}`,
			name: m.item_name || m.item_code || "",
			pct: num(m.percentage),
			balance: !!m.is_balance_item,
			storage: m.storage,
			stage: num(m.stage_row_id) || 1,
			color: MATERIAL_TONES[i % MATERIAL_TONES.length],
		})),
		stages,
	};
}

export const groupOf = (stages, i) =>
	stages.filter((stage) => num(stage.sequence_id) === num(stages[i].sequence_id));

function arrange(doc, stages) {
	const order = [...stages].sort((a, b) => num(a.sequence_id) - num(b.sequence_id));
	const positionOf = (no) => order.indexOf(doc.stages[no - 1]) + 1 || 1;
	(doc.materials || []).forEach((row) => (row.stage_row_id = positionOf(num(row.stage_row_id) || 1)));
	let sequence = 0;
	const sequences = order.map((stage, i) =>
		i && num(stage.sequence_id) === num(order[i - 1].sequence_id) ? sequence : ++sequence
	);
	order.forEach((stage, i) => (stage.sequence_id = sequences[i]));
	doc.stages.splice(0, doc.stages.length, ...order);
}

export function setRunsWith(doc, index, other) {
	const stage = doc.stages[index];
	stage.sequence_id = other === null ? num(stage.sequence_id) + 0.5 : num(doc.stages[other].sequence_id);
	arrange(doc, doc.stages);
}

export function moveStage(doc, from, to) {
	const stages = [...doc.stages];
	[stages[from], stages[to]] = [stages[to], stages[from]];
	[stages[from].sequence_id, stages[to].sequence_id] = [stages[to].sequence_id, stages[from].sequence_id];
	arrange(doc, stages);
}

export function insertStage(doc, index, stage) {
	const stages = [...doc.stages];
	stage.sequence_id = index ? num(stages[index - 1].sequence_id) + 0.5 : 0.5;
	stages.splice(index, 0, stage);
	arrange(doc, stages);
}

export function removeStage(doc, index) {
	arrange(
		doc,
		doc.stages.filter((_, i) => i !== index)
	);
}

export const READ_ONLY = Symbol("readOnly");
