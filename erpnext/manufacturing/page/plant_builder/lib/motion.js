const loops = new Set();
let held = false;

function play(el, spec) {
	if (el._loop) {
		el._loop.cancel();
		loops.delete(el._loop);
		el._loop = null;
	}
	if (!spec) return;

	const { keyframes, duration, delay = 0, easing = "linear" } = spec;
	el._loop = el.animate(keyframes, { duration, delay, easing, iterations: Infinity });
	loops.add(el._loop);
	if (held) el._loop.pause();
}

function bind(el, { value }) {
	const spec = JSON.stringify(value ?? null);
	if (spec === el._spec) return;
	el._spec = spec;
	play(el, value);
}

export const vLoop = { mounted: bind, updated: bind, unmounted: (el) => play(el, null) };

export function holdMotion(value) {
	held = value;
	loops.forEach((loop) => (value ? loop.pause() : loop.play()));
}
