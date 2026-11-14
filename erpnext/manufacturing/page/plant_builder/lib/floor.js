import { __ } from "./api";

export const MACHINE_STATUS = {
	Production: { mode: "run", theme: "green", dot: "bg-surface-green-5" },
	Idle: { mode: "hold", theme: "amber", dot: "bg-surface-amber-5" },
	Problem: { mode: "down", theme: "red", dot: "bg-surface-red-5" },
	Maintenance: { mode: "off", theme: "amber", dot: "bg-surface-amber-4" },
	Setup: { mode: "off", theme: "blue", dot: "bg-surface-blue-4" },
	Off: { mode: "off", theme: "gray", dot: "bg-surface-gray-5" },
};

export function newFloorDoc() {
	return {
		floor_name: "",
		company: window.frappe.defaults.get_default("company"),
		warehouse: "",
	};
}

export function toSceneFloor(floor, machines) {
	return {
		id: floor.name || "new",
		name: floor.floor_name || "",
		floor: true,
		product: { name: "", unit: __("Unit"), fillKg: 0, color: "gray" },
		materials: [],
		stages: machines.map((machine) => ({
			id: machine.name,
			machine_model: machine.machine_model,
			shapes: machine.shapes || [],
			name: machine.name,
			output: "",
			packaging: [],
			sequence: 0,
		})),
	};
}

export function floorView(machines, focus) {
	const modes = machines.map((machine) => MACHINE_STATUS[machine.status]?.mode || "off");
	return {
		level: Object.fromEntries(machines.map((machine, i) => [`s${i}`, machine.job ? 60 : 0])),
		mode: modes,
		working: modes.map((mode) => mode === "run"),
		flow: machines.map(() => false),
		active: machines.map((_, i) => focus === i),
		storeActive: false,
		fgActive: false,
		cartons: 0,
		crates: 1,
	};
}
