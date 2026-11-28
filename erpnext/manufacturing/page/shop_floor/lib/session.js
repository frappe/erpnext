import { computed, reactive } from "vue";
import { call } from "./api";

const EMPLOYEE_KEY = "shop-floor-employee";
const FLOOR_KEY = "shop-floor-plant-floor";

export const session = reactive({ context: null, employee: null, plantFloor: null });

export const isManager = computed(() => !!session.context?.is_manager);

export async function loadContext() {
	if (session.context) return;
	session.context = await call("get_context");
	session.employee = pickEmployee(session.context);
	const floors = session.context.plant_floors.map((row) => row.name);
	const floor = window.localStorage.getItem(FLOOR_KEY);
	session.plantFloor = floors.includes(floor) ? floor : floors[0] || null;
}

function pickEmployee(context) {
	const allowed = context.allowed_employees;
	if (allowed?.length === 1) return context.employee;
	const saved = JSON.parse(window.sessionStorage.getItem(EMPLOYEE_KEY) || "null");
	if (saved && (!allowed || allowed.includes(saved.name))) return saved;
	return allowed ? null : context.employee;
}

export const canSwitchOperator = computed(() => session.context?.can_switch_operator !== false);

export function signIn(employee) {
	session.employee = { name: employee.name, employee_name: employee.employee_name, image: employee.image };
	window.sessionStorage.setItem(EMPLOYEE_KEY, JSON.stringify(session.employee));
}

export function signOut() {
	session.employee = null;
	window.sessionStorage.removeItem(EMPLOYEE_KEY);
}

export function setPlantFloor(name) {
	session.plantFloor = name;
	window.localStorage.setItem(FLOOR_KEY, name);
}

export function usePolling(load, ms = 15000) {
	let timer = null;
	const onUpdate = (data) => ["Job Card", "Workstation"].includes(data?.doctype) && load();
	return {
		start() {
			timer = setInterval(load, ms);
			window.frappe.realtime.on("list_update", onUpdate);
		},
		stop() {
			clearInterval(timer);
			window.frappe.realtime.off("list_update", onUpdate);
		},
	};
}
