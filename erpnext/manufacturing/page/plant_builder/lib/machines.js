import MACHINE_SHAPES from "../../../doctype/workstation_type/machine_shapes.json";
import { num } from "./format";

const MACHINES = {
	Mixer: { label: "Mixer", stage: "Blending", icon: "lucide-blend", kind: "process", verb: "Mixing" },
	"Steam Kettle": {
		label: "Steam Kettle",
		stage: "Cooking",
		icon: "lucide-flame",
		kind: "process",
		verb: "Cooking",
	},
	Reactor: { label: "Reactor", stage: "Reaction", icon: "lucide-atom", kind: "process", verb: "Reacting" },
	Fermenter: {
		label: "Fermenter",
		stage: "Fermentation",
		icon: "lucide-flask-round",
		kind: "process",
		verb: "Fermenting",
	},
	Mill: { label: "Mill", stage: "Grinding", icon: "lucide-cog", kind: "process", verb: "Grinding" },
	Dryer: { label: "Dryer", stage: "Drying", icon: "lucide-wind", kind: "process", verb: "Drying" },
	Cooler: { label: "Cooler", stage: "Cooling", icon: "lucide-snowflake", kind: "process", verb: "Cooling" },
	"Filling Line": {
		label: "Filling Line",
		stage: "Filling",
		icon: "lucide-milk",
		kind: "pack",
		verb: "Filling",
	},
	"Bagging Line": {
		label: "Bagging Line",
		stage: "Bagging",
		icon: "lucide-package",
		kind: "pack",
		verb: "Bagging",
	},
	Machine: {
		label: "Machine",
		stage: "Processing",
		icon: "lucide-factory",
		kind: "process",
		verb: "Processing",
	},
};

export const machineOf = (model) => MACHINES[model] || MACHINES.Machine;
export const isPackingModel = (model) => machineOf(model).kind === "pack";

export const SHAPES = MACHINE_SHAPES.shapes;
export const PRESETS = MACHINE_SHAPES.presets;
const PACK_SIZE = { half: 0, height: 80 };

export const stageShapes = (stage) =>
	stage?.shapes?.length ? stage.shapes : PRESETS[stage?.machine_model || "Machine"] || [];

export function newShape(shape) {
	const spec = SHAPES[shape];
	return {
		shape,
		finish: spec.finish || "",
		x: 0,
		y: 0,
		z: 0,
		width: 0,
		depth: 0,
		radius: 0,
		height: 0,
		...spec.size,
		shows_level: 1,
		is_small: 0,
		shakes: 0,
	};
}

export function shapeExtent(shape) {
	const size = SHAPES[shape.shape]?.size || {};
	const round = "radius" in size;
	const flat = "width" in size;
	const halfX = round ? num(shape.radius) : flat ? num(shape.width) / 2 : 0;
	const halfY = round ? num(shape.radius) : flat ? num(shape.depth) / 2 : 0;
	const top = num(shape.z) + ("height" in size ? num(shape.height) : 0);
	return { x: num(shape.x), y: num(shape.y), z: num(shape.z), halfX, halfY, top, round };
}

export function machineBounds(shapes) {
	const bounds = { left: 0, right: 0, back: 0, front: 0, top: 0, round: false };
	let largest = 0;
	shapes.map(shapeExtent).forEach((e) => {
		bounds.left = Math.min(bounds.left, e.x - e.halfX);
		bounds.right = Math.max(bounds.right, e.x + e.halfX);
		bounds.back = Math.min(bounds.back, e.y - e.halfY);
		bounds.front = Math.max(bounds.front, e.y + e.halfY);
		bounds.top = Math.max(bounds.top, e.top);
		if (e.halfX * e.halfY > largest) [largest, bounds.round] = [e.halfX * e.halfY, e.round];
	});
	return bounds;
}

export function machineSize(stage) {
	if (isPackingModel(stage.machine_model)) return PACK_SIZE;
	const bounds = machineBounds(stageShapes(stage));
	return { half: Math.max(-bounds.left, bounds.right), height: bounds.top };
}

export const TONES = ["red", "amber", "cream", "blue", "green", "violet", "gray"];
export const MATERIAL_TONES = ["red", "blue", "cream", "amber", "gray", "violet", "green"];

export function toneFor(value) {
	const text = String(value || "");
	let hash = 0;
	for (let i = 0; i < text.length; i++) hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
	return TONES[hash % TONES.length];
}

export const SWATCH = {
	red: "bg-surface-red-5",
	amber: "bg-surface-amber-4",
	cream: "bg-surface-amber-2",
	blue: "bg-surface-blue-3",
	green: "bg-surface-green-4",
	violet: "bg-surface-violet-4",
	gray: "bg-surface-gray-4",
};

export const INK = {
	red: "text-ink-red-5",
	amber: "text-ink-amber-5",
	cream: "text-ink-amber-3",
	blue: "text-ink-blue-5",
	green: "text-ink-green-5",
	violet: "text-ink-violet-5",
	gray: "text-ink-gray-5",
};

export const STORAGE_OPTIONS = [
	{ label: "Tank", value: "Tank" },
	{ label: "Silo", value: "Silo" },
	{ label: "Sacks", value: "Sacks" },
];
