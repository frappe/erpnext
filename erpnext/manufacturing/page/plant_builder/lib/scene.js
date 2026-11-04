import { computed, inject, provide, ref } from "vue";
import { useEventListener } from "@vueuse/core";
import { machineOf, machineSize } from "./machines";
import { __ } from "./api";
import { clamp, fmt, plural } from "./format";

const VIEWS = { "3d": [-24, 56], top: [0, 0], front: [0, 72] };
const CAMERA = Symbol("camera");

export function useOrbitCamera() {
	const [rot, tilt] = VIEWS["3d"].map((angle) => ref(angle));
	const viewName = ref("3d");
	const zoom = ref(1);
	const pan = ref({ x: 0, y: 0 });
	const dragging = ref(false);
	const orbit = { on: false, panning: false, x: 0, y: 0, moved: 0 };
	provide(CAMERA, { rot, tilt });

	const animateTo = (toRot, toTilt) => turnCamera(rot, tilt, toRot, toTilt);
	const zoomBy = (step) => (zoom.value = clamp(zoom.value + step, 0.5, 3));
	const panBy = (dx, dy) => (pan.value = { x: pan.value.x + dx, y: pan.value.y + dy });

	function onWheel(e) {
		const sideways = e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY);
		if (sideways) panBy(-(e.deltaX || e.deltaY), 0);
		else zoomBy(-e.deltaY * 0.0015);
	}

	function setView(name) {
		viewName.value = name;
		animateTo(...VIEWS[name]);
	}

	function fit() {
		zoom.value = 1;
		pan.value = { x: 0, y: 0 };
		setView("3d");
	}

	function onDown(e) {
		if (e.button > 2) return;
		const panning = e.button !== 0 || e.shiftKey;
		Object.assign(orbit, { on: true, panning, x: e.clientX, y: e.clientY, moved: 0 });
	}

	useEventListener(window, "pointermove", (e) => {
		if (!orbit.on) return;
		const dx = e.clientX - orbit.x;
		const dy = e.clientY - orbit.y;
		orbit.moved += Math.abs(dx) + Math.abs(dy);
		dragging.value = orbit.moved > 4;
		if (orbit.panning) {
			panBy(dx, dy);
		} else {
			rot.value += dx * 0.35;
			tilt.value = clamp(tilt.value - dy * 0.3, 0, 80);
		}
		Object.assign(orbit, { x: e.clientX, y: e.clientY });
	});
	useEventListener(window, "pointerup", () => {
		orbit.on = false;
		dragging.value = false;
	});

	return {
		viewName,
		rot,
		tilt,
		zoom,
		pan,
		dragging,
		animateTo,
		setView,
		fit,
		zoomBy,
		panBy,
		onWheel,
		onDown,
	};
}

export function useFacing(normals, margin = 0.01) {
	const camera = inject(CAMERA, null);
	return computed(() => {
		const angles = typeof normals === "function" ? normals() : normals;
		if (!camera) return 2 ** angles.length - 1;
		const tilt = Math.sin((camera.tilt.value * Math.PI) / 180);
		return angles.reduce((mask, angle, i) => {
			const facing = Math.cos(((angle + camera.rot.value) * Math.PI) / 180) * tilt;
			return facing > margin ? mask | (1 << i) : mask;
		}, 0);
	});
}

function turnCamera(rot, tilt, toRot, toTilt) {
	const from = [rot.value, tilt.value];
	const start = performance.now();
	const step = (now) => {
		const p = Math.min(1, (now - start) / 350);
		const e = 1 - (1 - p) ** 3;
		rot.value = from[0] + (toRot - from[0]) * e;
		tilt.value = from[1] + (toTilt - from[1]) * e;
		if (p < 1) requestAnimationFrame(step);
	};
	requestAnimationFrame(step);
}

export function previewView(plant, animate, focus) {
	const level = {};
	plant.materials.forEach((m) => (level[`m:${m.id}`] = 75));
	plant.stages.forEach((_, i) => (level[`s${i}`] = animate ? 60 : 0));
	const all = (value) => plant.stages.map(() => value);
	return {
		level,
		mode: all(animate ? "run" : "off"),
		working: all(animate),
		flow: all(animate),
		active: plant.stages.map((_, i) => focus === i),
		storeActive: false,
		fgActive: false,
		cartons: animate ? 0.5 : 0,
		crates: 1,
	};
}

function stationTag(plant, station, view, holding) {
	const machine = machineOf(station.stage.machine_model);
	const title = station.stage.name || __(machine.label);
	const active = view.active[station.i];
	const sub = holding ? holding(station.i) : __(machine.label);
	if (!station.pack) {
		return {
			id: `s${station.i}`,
			x: station.x,
			y: station.y,
			z: machineSize(station.stage).height + 12,
			title,
			sub,
			active,
		};
	}
	return { id: `s${station.i}`, x: station.zone.x + 205, y: station.y - 30, z: 84, title, sub, active };
}

function storeTag(item, stock) {
	const key = `m:${item.m.id}`;
	const sacks = item.shape === "sacks";
	const sub = stock ? stock(item.m) : `${fmt(item.m.pct)}%`;
	return {
		id: key,
		x: item.x,
		y: sacks ? item.y + 30 : item.y,
		z: sacks ? 46 : item.h + 6,
		title: item.m.name || "",
		sub,
	};
}

export function buildTags(plant, layout, view, live = {}) {
	const tags = [
		...layout.store.items.map((item) => storeTag(item, live.stock)),
		...layout.stations.map((station) => stationTag(plant, station, view, live.holding)),
	];
	if (!layout.fg) return tags;

	const unit = plural(plant.product.unit).toLowerCase();
	const sub = live.packed !== undefined ? `${fmt(live.packed)} ${unit}` : plant.product.name || "";
	return [
		...tags,
		{
			id: "fg",
			x: layout.fg.x + 160,
			y: layout.fg.y + 105,
			z: 70,
			title: __("Finished goods"),
			sub,
			active: view.fgActive,
		},
	];
}
