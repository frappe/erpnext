import { computed, onBeforeUnmount, reactive, ref } from "vue";
import { __, call } from "./api";
import { holdClock, levels, setLevels, tween } from "./clock";
import { machineOf } from "./machines";
import { toScenePlant } from "./plant";
import { fmt, num, round } from "./format";

const CHARGE_MS = 2500;
const PREVIEW_MS = 300;

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
		preview: {},
		pending: {},
		replan: {},
		picks: {},
	});
	const now = ref(Date.now());
	const capacity = {};
	const previewTimers = {};
	let previewSeq = 0;
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
			? __("Charging {0}", [stage.workstation])
			: __("{0} · {1} of {2} min", [__(machine.verb), fmt(minutes), fmt(stage.planned_minutes)]);
	}

	const activity = computed(() => {
		const busy = stages.value.filter((s) => ["charging", "processing"].includes(s.phase));
		if (!busy.length) return paused.value ? { label: __("Work Order on hold"), progress: null } : null;
		const label = busy.length > 1 ? busy.map((s) => s.stage_name).join(" · ") : activityOf(busy[0]);
		return { label: paused.value ? __("On hold · {0}", [label]) : label, progress: progressOf(busy[0]) };
	});

	function seedLocal(data) {
		data.stages.forEach((stage) => {
			const waiting = stage.inputs.map((row) => row.waiting_qty).join();
			const key = `${stage.job_card?.name}:${stage.phase}:${waiting}`;
			if (local.seeded[stage.idx] === key) return;
			local.seeded[stage.idx] = key;
			local.picks[stage.idx] = {};
			if (stage.job_card) {
				local.actual[stage.idx] = Object.fromEntries(
					stage.items.map((row) => [row.name, row.is_input ? row.waiting_qty : row.required_qty])
				);
			}
			clearTimeout(previewTimers[stage.idx]);
			delete local.pending[stage.idx];
			delete local.preview[stage.idx];
			local.replan[stage.idx] = true;
			if (stage.phase === "ready") schedulePreview(stage, 0);
			local.output[stage.idx] = stage.output.expected_qty || stage.output.planned_qty;
			local.rejected[stage.idx] = 0;
			if (stage.quality) {
				local.readings[stage.idx] = Object.fromEntries(
					stage.quality.parameters.map((p) => [p.specification, ""])
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
				{
					job_card: stage.job_card.name,
					quantities: local.actual[stage.idx],
					picks: local.picks[stage.idx],
				},
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

	function schedulePreview(stage, delay = PREVIEW_MS) {
		clearTimeout(previewTimers[stage.idx]);
		const request = (local.pending[stage.idx] = ++previewSeq);
		previewTimers[stage.idx] = setTimeout(() => previewLot(stage, request), delay);
	}

	async function previewLot(stage, request) {
		const replan = local.replan[stage.idx];
		const actual = local.actual[stage.idx];
		const inputs = stage.items.filter((row) => row.is_input).map((row) => row.name);
		try {
			const preview = await call("preview_lot", {
				work_order: workOrder,
				job_card: stage.job_card.name,
				quantities: replan ? Object.fromEntries(inputs.map((name) => [name, actual[name]])) : actual,
			});
			if (local.pending[stage.idx] !== request) return;
			if (replan) {
				stage.items
					.filter((row) => !row.is_input)
					.forEach((row) => (actual[row.name] = preview.items[row.name].qty));
				local.replan[stage.idx] = false;
			}
			local.preview[stage.idx] = preview;
		} finally {
			if (local.pending[stage.idx] === request) delete local.pending[stage.idx];
		}
	}

	function setPass(stage, row, value) {
		const share = row.waiting_qty ? num(value) / row.waiting_qty : 0;
		stage.items
			.filter((other) => other.is_input)
			.forEach(
				(other) =>
					(local.actual[stage.idx][other.name] =
						other === row ? value : round(other.waiting_qty * share, 3))
			);
		local.replan[stage.idx] = true;
		schedulePreview(stage);
	}

	function setMaterial(stage, row, value) {
		local.actual[stage.idx][row.name] = value;
		schedulePreview(stage);
	}

	const pickOf = (stage, row) => local.picks[stage.idx]?.[row.name];
	const pickedQty = (pick) =>
		pick.serial_nos?.length || Object.values(pick.batches || {}).reduce((sum, qty) => sum + num(qty), 0);

	function setPick(stage, row, pick) {
		if (!pick) return delete local.picks[stage.idx][row.name];
		local.picks[stage.idx][row.name] = pick;
		if (!row.is_balance_item) setMaterial(stage, row, round(pickedQty(pick), 3));
	}

	function pickErrors(stage) {
		return stage.items
			.filter((row) => pickOf(stage, row))
			.filter((row) => round(pickedQty(pickOf(stage, row)), 3) !== round(usedOf(stage, row), 3))
			.map((row) =>
				__("Picked {0} {1} of {2}, but this lot uses {3} {1}", [
					fmt(pickedQty(pickOf(stage, row))),
					row.uom,
					row.item_name,
					fmt(usedOf(stage, row)),
				])
			);
	}

	const getPickOptions = (stage, row) =>
		call("get_serial_batch_options", {
			work_order: workOrder,
			job_card: stage.job_card.name,
			row: row.name,
		});

	const previewOf = (stage) => local.preview[stage.idx];
	const plannedOf = (stage, row) => previewOf(stage)?.items[row.name]?.planned_qty ?? row.required_qty;
	const usedOf = (stage, row) => previewOf(stage)?.items[row.name]?.qty ?? row.transferred_qty;
	const isOff = (stage, row) => !!previewOf(stage)?.items[row.name]?.is_off;
	const isPreviewing = (stage) => !!local.pending[stage.idx];

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
		previewOf,
		plannedOf,
		usedOf,
		isOff,
		isPreviewing,
		pickOf,
		pickedQty,
		setPick,
		pickErrors,
		getPickOptions,
		setPass,
		setMaterial,
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
