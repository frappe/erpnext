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
		name: s.stage_name,
		output: s.semi_finished_good || "",
		packaging: (doc.packing_materials || []).map((p) => p.item_name || p.item_code),
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
			color: MATERIAL_TONES[i % MATERIAL_TONES.length],
		})),
		stages,
	};
}
