export const STATUS_COLORS = {
	Open: "var(--surface-blue-7)",
	Working: "var(--surface-blue-5)",
	"Pending Review": "var(--surface-violet-7)",
	Overdue: "var(--surface-red-6)",
	Completed: "var(--surface-green-7)",
	Cancelled: "var(--surface-gray-5)",
};
export const OTHER_STATUS = "var(--surface-gray-4)";

export const OUTCOME_COLORS = {
	"On Time": "var(--surface-green-7)",
	Late: "var(--surface-red-6)",
	"No Due Date": "var(--surface-gray-4)",
	"Still Open": "var(--surface-blue-7)",
	Cancelled: "var(--surface-gray-6)",
};

const AVATAR_THEMES = ["blue", "green", "amber", "red", "violet", "gray"];

export function avatarTheme(label = "") {
	let hash = 0;
	for (const char of label) hash = (hash * 31 + char.charCodeAt(0)) | 0;
	return AVATAR_THEMES[Math.abs(hash) % AVATAR_THEMES.length];
}
