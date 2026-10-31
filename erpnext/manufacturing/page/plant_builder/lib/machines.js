export const MACHINES = {
	mixer: {
		label: "Mixer",
		stage: "Blending",
		icon: "lucide-blend",
		kind: "process",
		verb: "Mixing",
		half: 56,
		height: 162,
	},
	kettle: {
		label: "Steam Kettle",
		stage: "Cooking",
		icon: "lucide-flame",
		kind: "process",
		verb: "Cooking",
		half: 62,
		height: 110,
	},
	reactor: {
		label: "Reactor",
		stage: "Reaction",
		icon: "lucide-atom",
		kind: "process",
		verb: "Reacting",
		half: 54,
		height: 186,
	},
	fermenter: {
		label: "Fermenter",
		stage: "Fermentation",
		icon: "lucide-flask-round",
		kind: "process",
		verb: "Fermenting",
		half: 46,
		height: 180,
	},
	mill: {
		label: "Mill",
		stage: "Grinding",
		icon: "lucide-cog",
		kind: "process",
		verb: "Grinding",
		half: 58,
		height: 92,
	},
	dryer: {
		label: "Dryer",
		stage: "Drying",
		icon: "lucide-wind",
		kind: "process",
		verb: "Drying",
		half: 82,
		height: 70,
	},
	cooler: {
		label: "Cooler",
		stage: "Cooling",
		icon: "lucide-snowflake",
		kind: "process",
		verb: "Cooling",
		half: 44,
		height: 100,
	},
	filler: {
		label: "Filling Line",
		stage: "Filling",
		icon: "lucide-milk",
		kind: "pack",
		verb: "Filling",
		half: 0,
		height: 80,
	},
	bagger: {
		label: "Bagging Line",
		stage: "Bagging",
		icon: "lucide-package",
		kind: "pack",
		verb: "Bagging",
		half: 0,
		height: 80,
	},
	generic: {
		label: "Machine",
		stage: "Processing",
		icon: "lucide-factory",
		kind: "process",
		verb: "Processing",
		half: 48,
		height: 96,
	},
};

const MODEL_KEYS = {
	Mixer: "mixer",
	"Steam Kettle": "kettle",
	Reactor: "reactor",
	Fermenter: "fermenter",
	Mill: "mill",
	Dryer: "dryer",
	Cooler: "cooler",
	"Filling Line": "filler",
	"Bagging Line": "bagger",
};

export const machineKey = (model) => MODEL_KEYS[model] || "generic";
export const machineOf = (model) => MACHINES[machineKey(model)];
export const isPack = (stage) => MACHINES[stage?.machine]?.kind === "pack";

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
