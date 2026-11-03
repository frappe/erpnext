import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { holdMotion } from "./motion";

export const clock = ref(0);
export const levels = reactive({});

const scenes = new Set();
const jobs = new Set();
const state = { held: false, last: 0, ms: 0, running: false };

const isVisible = () => [...scenes].some((el) => el.isConnected && el.offsetParent !== null);

function frame(now) {
	const dt = state.last ? Math.min(now - state.last, 100) : 0;
	state.last = now;
	if (!state.held && isVisible()) {
		state.ms += dt;
		clock.value = state.ms / 1000;
		jobs.forEach((job) => job(state.ms));
	}

	if (scenes.size) {
		requestAnimationFrame(frame);
	} else {
		state.running = false;
	}
}

export function useClock(elementRef) {
	onMounted(() => {
		scenes.add(elementRef.value);
		if (!state.running) {
			state.running = true;
			state.last = 0;
			requestAnimationFrame(frame);
		}
	});
	onBeforeUnmount(() => scenes.delete(elementRef.value));
}

export function holdClock(held) {
	state.held = held;
	holdMotion(held);
}

export function tween(key, to, ms, linear = false) {
	const from = levels[key] ?? 0;
	const start = state.ms;
	const job = (t) => {
		const p = ms ? Math.min(1, (t - start) / ms) : 1;
		levels[key] = from + (to - from) * (linear ? p : 1 - (1 - p) ** 2);
		if (p >= 1) jobs.delete(job);
	};
	jobs.add(job);
}

export function setLevels(values) {
	Object.keys(levels).forEach((key) => delete levels[key]);
	Object.assign(levels, values);
}
