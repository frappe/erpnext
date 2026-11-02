import { computed, onBeforeUnmount, reactive, ref } from "vue";
import { call } from "./api";
import { holdClock, levels, setLevels, tween } from "./clock";
import { machineOf } from "./machines";
import { toScenePlant } from "./plant";
import { fmt, num, round } from "./format";

const CHARGE_MS = 2500;

const rowKey = (row) => row.name || row.item_code;

export function useRun(workOrder) {
	const state = ref(null);
	const busy = ref(false);
	const local = reactive({
		charging: null,
		review: {},
		actual: {},
		output: {},
		rejected: {},
		readings: {},
		seeded: {},
	});
	const now = ref(Date.now());
	const capacity = {};
	let offset = 0;

	const timer = setInterval(() => (now.value = Date.now()), 1000);
	onBeforeUnmount(() => clearInterval(timer));

	const plant = computed(
		() =>
			state.value &&
			toScenePlant(state.value.plant.doc, state.value.plant.machines, state.value.plant.item)
	);
	const workOrderData = computed(() => state.value?.work_order);
	const paused = computed(() => !!workOrderData.value?.is_paused);
	const status = computed(() => {
		const order = workOrderData.value;
		if (!order) return "";
		if (order.status === "Completed") return order.status;
		if (paused.value) return "On Hold";
		if ((state.value.stages || []).some((stage) => stage.breakdown)) return "Breakdown";
		const started = (state.value.stages || []).some((stage) => stage.phase !== "waiting");
		return order.docstatus === 1 && started ? "In Process" : "Not Started";
	});

	const serverNow = () => now.value + offset;
	const runningSeconds = (since) =>
		since ? Math.max(0, (serverNow() - new Date(since).getTime()) / 1000) : 0;
	const elapsed = computed(() => {
		const order = workOrderData.value;
		return order ? Math.floor(order.worked_seconds + runningSeconds(order.running_since)) : 0;
	});

	function stageSeconds(stage) {
		const card = stage.job_card;
		return card ? Math.floor(card.worked_seconds + runningSeconds(card.running_since)) : 0;
	}

	function phaseOf(stage) {
		if (local.charging === stage.idx) return "charging";
		if (stage.phase === "processing" && local.review[stage.idx]) return "review";
		return stage.phase;
	}

	const stages = computed(() =>
		(state.value?.stages || []).map((stage) => ({ ...stage, phase: phaseOf(stage) }))
	);
	const isActive = (stage) => stage.can_start || !["waiting", "done"].includes(stage.phase);
	const hasActiveStage = computed(() => stages.value.some(isActive));

	function progressOf(stage) {
		if (stage.phase === "charging") return 100;
		return Math.min(100, (stageSeconds(stage) / 60 / Math.max(stage.planned_minutes, 1)) * 100);
	}

	function activityOf(stage) {
		const machine = machineOf(stage.machine_model);
		const minutes = Math.round(stageSeconds(stage) / 60);
		return stage.phase === "charging"
			? `Charging ${stage.workstation}`
			: `${machine.verb} · ${fmt(minutes)} of ${fmt(stage.planned_minutes)} min`;
	}

	const activity = computed(() => {
		const busy = stages.value.filter((s) => ["charging", "processing"].includes(s.phase));
		if (!busy.length) return paused.value ? { label: "Work Order on hold", progress: null } : null;
		const label = busy.length > 1 ? busy.map((s) => s.stage_name).join(" · ") : activityOf(busy[0]);
		return { label: paused.value ? `On hold · ${label}` : label, progress: progressOf(busy[0]) };
	});

	function seedLocal(data) {
		data.stages.forEach((stage) => {
			const waiting = stage.inputs.map((row) => row.waiting_qty).join();
			const key = `${stage.job_card?.name}:${stage.phase}:${waiting}`;
			if (local.seeded[stage.idx] === key) return;
			local.seeded[stage.idx] = key;
			local.actual[stage.idx] = Object.fromEntries(
				stage.items.map((row) => [rowKey(row), row.is_input ? row.waiting_qty : row.required_qty])
			);
			if (stage.phase === "ready") rescale(stage);
			local.output[stage.idx] = stage.output.expected_qty || stage.output.planned_qty;
			local.rejected[stage.idx] = 0;
			if (stage.quality && !local.readings[stage.idx]) {
				local.readings[stage.idx] = Object.fromEntries(
					stage.quality.parameters.map((p) => [
						p.specification,
						round((num(p.min_value) + num(p.max_value)) / 2, 2),
					])
				);
			}
		});
	}

	function targetLevels(data) {
		const values = { cartons: num(data.work_order.produced_qty) / Math.max(num(data.work_order.qty), 1) };
		const store = data.levels.store;
		data.plan.materials.forEach((row) => {
			capacity[row.item_code] ??= Math.max(num(store[row.item_code]), row.qty * 1.25, 1) / 0.8;
			values[`m:${row.item_code}`] = Math.min(
				100,
				(num(store[row.item_code]) / capacity[row.item_code]) * 100
			);
		});
		data.stages.forEach((stage, i) => {
			const machine = data.plant.machines[stage.workstation] || {};
			const limit = num(machine.batch_capacity) || num(data.plan.input_weight) * 1.25 || 1;
			values[`s${i}`] = Math.min(100, (num(data.levels.machines[stage.workstation]) / limit) * 100);
		});
		const packing = data.plan.packing_materials[0];
		if (packing) {
			capacity.packing ??= Math.max(num(store[packing.item_code]), packing.qty, 1);
			values.crates = num(store[packing.item_code]) / capacity.packing;
		}
		return values;
	}

	function syncLevels(data, animateMs) {
		const values = targetLevels(data);
		if (!animateMs || !Object.keys(levels).length) return setLevels(values);
		Object.entries(values).forEach(([key, value]) => tween(key, value, animateMs));
	}

	function load(data, animateMs = 0) {
		offset = new Date(data.now).getTime() - Date.now();
		seedLocal(data);
		syncLevels(data, animateMs);
		state.value = data;
		holdClock(!!data.work_order.is_paused);
	}

	const refresh = async () => load(await call("get_run", { work_order: workOrder }), 600);

	async function act(method, args = {}, animateMs = 600) {
		busy.value = true;
		try {
			load(await call(method, { work_order: workOrder, ...args }), animateMs);
		} finally {
			busy.value = false;
		}
	}

	async function consume(stage) {
		local.charging = stage.idx;
		try {
			await act(
				"consume_materials",
				{ job_card: stage.job_card.name, quantities: actualQuantities(stage) },
				CHARGE_MS
			);
			setTimeout(() => (local.charging = null), CHARGE_MS);
		} catch (error) {
			local.charging = null;
			throw error;
		}
	}

	async function produce(stage) {
		const readings = Object.entries(local.readings[stage.idx] || {}).map(([specification, value]) => ({
			specification,
			reading_value: value,
			status: "Accepted",
		}));
		await act("produce_output", {
			job_card: stage.job_card.name,
			output_qty: local.output[stage.idx],
			rejected_qty: local.rejected[stage.idx],
			readings,
		});
		delete local.review[stage.idx];
	}

	const weightOf = (row, qty) => num(qty) / (row.weight_factor || 1);

	function shareOf(stage) {
		const inputs = stage.items.filter((row) => row.is_input);
		if (!inputs.length) return 1;
		const planned = inputs.reduce((sum, row) => sum + weightOf(row, row.planned_qty), 0);
		const passed = inputs.reduce(
			(sum, row) => sum + weightOf(row, local.actual[stage.idx]?.[rowKey(row)]),
			0
		);
		return planned ? passed / planned : 0;
	}

	function plannedOutput(stage) {
		const output = stage.output;
		if (!stage.items.some((row) => row.is_input)) return output.planned_qty;
		const roundDown = output.whole_number
			? (qty) => Math.floor(qty + 0.000001)
			: (qty) => Math.floor(qty * 1000 + 0.000001) / 1000;
		const total = output.operation_qty * (output.done_share + shareOf(stage));
		const planned = roundDown(total) - output.done_qty;
		return roundDown(Math.max(Math.min(planned, output.limit ?? Infinity), 0));
	}

	function scaleOf(stage) {
		if (!stage.items.some((row) => row.is_input)) return 1;
		return stage.output.operation_qty ? plannedOutput(stage) / stage.output.operation_qty : 0;
	}

	function plannedOf(stage, row) {
		if (stage.phase !== "ready") return row.required_qty;
		return row.is_input ? row.waiting_qty : round(row.planned_qty * scaleOf(stage), 3);
	}

	function rescale(stage) {
		stage.items
			.filter((row) => !row.is_input && !row.is_balance_item)
			.forEach((row) => (local.actual[stage.idx][rowKey(row)] = plannedOf(stage, row)));
	}

	function setPass(stage, row, value) {
		const share = row.waiting_qty ? num(value) / row.waiting_qty : 0;
		stage.items
			.filter((other) => other.is_input && other !== row)
			.forEach(
				(other) => (local.actual[stage.idx][rowKey(other)] = round(other.waiting_qty * share, 3))
			);
		local.actual[stage.idx][rowKey(row)] = value;
		rescale(stage);
	}

	function actualOf(stage, row) {
		if (!row.is_balance_item) return num(local.actual[stage.idx]?.[rowKey(row)]);
		const shift = stage.items
			.filter((r) => !r.is_input && !r.is_balance_item && r.weight_factor)
			.reduce(
				(sum, r) =>
					sum + (num(local.actual[stage.idx]?.[rowKey(r)]) - plannedOf(stage, r)) / r.weight_factor,
				0
			);
		return round(plannedOf(stage, row) - shift * (row.weight_factor || 1), 3);
	}

	const actualQuantities = (stage) =>
		Object.fromEntries(stage.items.map((row) => [row.name, actualOf(stage, row)]));

	return {
		state,
		busy,
		local,
		plant,
		stages,
		status,
		paused,
		elapsed,
		activity,
		activityOf,
		isActive,
		hasActiveStage,
		stageSeconds,
		progressOf,
		actualOf,
		plannedOf,
		plannedOutput,
		setPass,
		refresh,
		consume,
		produce,
		setQty: (qty) => act("set_run_qty", { qty }),
		start: (stage) => act("start_run", { job_card: stage?.job_card?.name }),
		reportBreakdown: (stage) => act("report_breakdown", { job_card: stage.job_card.name }),
		restartMachine: (stage, values) =>
			act("restart_machine", { job_card: stage.job_card.name, ...values }),
		secondsSince: runningSeconds,
		pause: () => act("pause_run"),
		resume: () => act("resume_run"),
		openReview: (stage) => (local.review[stage.idx] = true),
	};
}
