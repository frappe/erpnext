import { num } from "./format";
import { isPackingModel } from "./machines";

const OPERATION_FIELDS = [
	"name",
	"operation_id",
	"operation",
	"workstation",
	"workstation_type",
	"time_in_mins",
	"output_item",
	"yield_percentage",
	"sequence_id",
];
const MATERIAL_FIELDS = ["name", "operation_id", "item_code", "qty", "is_balance_item", "storage"];

const pick = (row, fields) => Object.fromEntries(fields.map((field) => [field, row[field] ?? null]));

export function fromDesign(design, typeModels = {}) {
	const batch = num(design.qty) || 1;
	const stages = (design.operations || []).map((row) => ({
		...pick(row, OPERATION_FIELDS),
		stage_name: row.operation,
		semi_finished_good: row.output_item,
		machine_model: typeModels[row.workstation_type] || null,
	}));
	const last = stages.at(-1);
	const packingId = isPackingModel(last?.machine_model) ? last.operation_id : undefined;
	const stageOf = (row) => stages.findIndex((stage) => stage.operation_id === row.operation_id) + 1 || 1;
	const rows = design.materials || [];
	return {
		production_item: design.item_code,
		batch_size: batch,
		stages,
		materials: rows
			.filter((row) => row.operation_id !== packingId)
			.map((row) => ({
				name: row.name,
				item_code: row.item_code,
				qty: num(row.qty) * batch,
				is_balance_item: row.is_balance_item ? 1 : 0,
				storage: row.storage || "Tank",
				stage_row_id: stageOf(row),
			})),
		packing_materials: rows
			.filter((row) => row.operation_id === packingId)
			.map((row) => ({ name: row.name, item_code: row.item_code, qty_per_unit: num(row.qty) })),
	};
}

export function toDesign(doc) {
	const batch = num(doc.batch_size) || 1;
	const stages = doc.stages;
	const packingId = stages.at(-1)?.operation_id;
	const operations = stages.map((stage, i) => ({
		...pick(stage, OPERATION_FIELDS),
		operation: stage.operation || null,
		output_item: i === stages.length - 1 ? null : stage.semi_finished_good || null,
	}));
	const idOf = (row) => (stages[(row.stage_row_id || 1) - 1] || stages[0])?.operation_id ?? null;
	const materials = [
		...doc.materials.map((row) => ({
			...pick(row, MATERIAL_FIELDS),
			operation_id: idOf(row),
			qty: num(row.qty) / batch,
		})),
		...doc.packing_materials.map((row) => ({
			name: row.name,
			operation_id: packingId ?? null,
			item_code: row.item_code,
			qty: num(row.qty_per_unit),
			is_balance_item: 0,
			storage: "Tank",
		})),
	];
	return { operations, materials: materials.map((row) => pick(row, MATERIAL_FIELDS)) };
}

export function designRows(design) {
	return {
		operations: (design.operations || []).map((row) => pick(row, OPERATION_FIELDS)),
		materials: (design.materials || []).map((row) => pick(row, MATERIAL_FIELDS)),
	};
}

const NUMBERS = ["operation_id", "time_in_mins", "yield_percentage", "sequence_id", "qty", "is_balance_item"];

export const rowsKey = (rows) =>
	JSON.stringify(rows, (key, value) =>
		NUMBERS.includes(key) ? Math.round(num(value) * 1e9) / 1e9 : value ?? null
	);
