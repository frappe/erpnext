<template>
	<div class="flex w-full flex-col gap-2">
		<div class="flex items-center gap-2">
			<TabButtons v-model="mode" :options="tabs" size="sm" />
			<!-- the picker opens with the tab; this brings it back after a cancel -->
			<Button
				v-if="mode === 'load'"
				class="ms-auto"
				variant="ghost"
				size="sm"
				:label="__('Choose image')"
				@click="fileEl?.click()"
			/>
			<Button
				:class="mode === 'load' ? '' : 'ms-auto'"
				variant="ghost"
				size="sm"
				:label="__('Clear')"
				@click="clear"
			/>
		</div>

		<!-- white in both themes, like the paper the signature is printed on: the ink
		     colour is fixed so the signed copy reads the same, and would vanish on dark -->
		<div class="relative w-full rounded border border-outline-gray-2 bg-white">
			<canvas
				ref="canvasEl"
				class="w-full touch-none"
				role="img"
				:aria-label="__('Signature')"
				:style="{ height: `${height}px` }"
				@pointerdown="onDown"
				@pointermove="onMove"
				@pointerup="onUp"
				@pointercancel="onUp"
				@pointerleave="onUp"
			/>
			<div class="pointer-events-none absolute inset-x-6 bottom-8 border-b border-outline-gray-2" />
			<!-- A plain input, not frappe-ui's FileUploader: that one uploads to the
			     server and hands back a File record, and the signature must stay a
			     data URL that goes into the document's own field. -->
			<input ref="fileEl" type="file" accept="image/*" class="hidden" @change="onFile" />
		</div>

		<p class="text-xs text-ink-gray-5">{{ hint }}</p>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Button, TabButtons } from "frappe-ui";
import { __ } from "@app/lib/translate";

const props = withDefaults(
	defineProps<{
		/** PNG data URL of the signature. Empty string when nothing is signed. */
		modelValue?: string;
		height?: number;
	}>(),
	{ modelValue: "", height: 150 }
);

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const tabs = computed(() => [
	{ label: __("Draw"), value: "draw" },
	{ label: __("Load"), value: "load" },
]);

const canvasEl = ref<HTMLCanvasElement | null>(null);
const fileEl = ref<HTMLInputElement | null>(null);
const mode = ref("draw");
const hasInk = ref(false);

const hint = computed(() =>
	mode.value === "draw" ? __("Draw your signature above.") : __("Choose an image of your signature.")
);

/** Device pixels per CSS pixel, so the line is crisp on a retina screen. */
function ratio(): number {
	return typeof window === "undefined" ? 1 : window.devicePixelRatio || 1;
}

function context(): CanvasRenderingContext2D | null {
	return canvasEl.value?.getContext("2d") ?? null;
}

/** Size the backing store to the element, then scale so we can draw in CSS pixels. */
function resize() {
	const canvas = canvasEl.value;
	if (!canvas) return;
	const rect = canvas.getBoundingClientRect();
	if (!rect.width) return;
	const scale = ratio();
	canvas.width = Math.round(rect.width * scale);
	canvas.height = Math.round(rect.height * scale);
	const ctx = context();
	if (!ctx) return;
	ctx.scale(scale, scale);
	ctx.lineCap = "round";
	ctx.lineJoin = "round";
	ctx.strokeStyle = "#1f272e";
	ctx.fillStyle = "#1f272e";
}

function wipe() {
	const canvas = canvasEl.value;
	const ctx = context();
	if (!canvas || !ctx) return;
	ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// —— drawing ——
//
// Each segment runs midpoint-to-midpoint with the sampled point as the curve's
// control, so consecutive segments share an endpoint and the line is unbroken.
// Drawing point-to-midpoint instead leaves the other half of every segment
// undrawn, which reads as a dashed line.
//
// Only the newest segment is stroked. Re-stroking one long path would redraw
// every earlier segment on each move: slower the longer you sign, and darker
// wherever the line crosses itself.

type Point = { x: number; y: number; at: number };

const drawing = ref(false);
let previous: Point | null = null;
let lastMidpoint: Point | null = null;
let width = 2;

function pointOf(event: PointerEvent): Point {
	const rect = canvasEl.value!.getBoundingClientRect();
	return { x: event.clientX - rect.left, y: event.clientY - rect.top, at: event.timeStamp };
}

function midpointOf(a: Point, b: Point): Point {
	return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, at: b.at };
}

/**
 * Thinner the faster the pen moves, which is what makes a drawn line read as
 * handwriting rather than wire. Eased against the previous width so the stroke
 * doesn't step between samples.
 */
function widthFor(from: Point, to: Point): number {
	const distance = Math.hypot(to.x - from.x, to.y - from.y);
	const elapsed = Math.max(1, to.at - from.at);
	const speed = distance / elapsed;
	const target = Math.max(0.9, Math.min(2.6, 2.6 - speed * 1.6));
	width = width * 0.65 + target * 0.35;
	return width;
}

function onDown(event: PointerEvent) {
	if (mode.value !== "draw") return;
	const ctx = context();
	if (!ctx) return;
	drawing.value = true;
	width = 2;
	canvasEl.value?.setPointerCapture(event.pointerId);
	previous = pointOf(event);
	lastMidpoint = previous;
	// a tap with no movement should still leave a mark
	ctx.beginPath();
	ctx.arc(previous.x, previous.y, width / 2, 0, Math.PI * 2);
	ctx.fill();
	hasInk.value = true;
}

function segmentTo(ctx: CanvasRenderingContext2D, point: Point) {
	if (!previous || !lastMidpoint) return;
	const midpoint = midpointOf(previous, point);
	ctx.beginPath();
	ctx.lineWidth = widthFor(previous, point);
	ctx.moveTo(lastMidpoint.x, lastMidpoint.y);
	ctx.quadraticCurveTo(previous.x, previous.y, midpoint.x, midpoint.y);
	ctx.stroke();
	lastMidpoint = midpoint;
	previous = point;
}

function onMove(event: PointerEvent) {
	if (!drawing.value || !previous || !lastMidpoint) return;
	const ctx = context();
	if (!ctx) return;

	// The browser batches pointermove, so a quick stroke arrives as a handful of
	// far-apart samples and draws as straight runs. getCoalescedEvents gives back
	// every point it merged, which is most of what makes a fast stroke look drawn
	// rather than plotted.
	const samples = event.getCoalescedEvents?.() ?? [];
	for (const sample of samples.length ? samples : [event]) {
		segmentTo(ctx, pointOf(sample));
	}
	hasInk.value = true;
}

function onUp(event: PointerEvent) {
	if (!drawing.value) return;
	const ctx = context();
	// close the gap between the last midpoint and where the pen actually lifted
	if (ctx && previous && lastMidpoint) {
		ctx.beginPath();
		ctx.moveTo(lastMidpoint.x, lastMidpoint.y);
		ctx.lineTo(previous.x, previous.y);
		ctx.stroke();
	}
	drawing.value = false;
	previous = null;
	lastMidpoint = null;
	canvasEl.value?.releasePointerCapture?.(event.pointerId);
	emitImage();
}

// —— uploading ——

function onFile(event: Event) {
	const file = (event.target as HTMLInputElement).files?.[0];
	if (!file) return;
	const reader = new FileReader();
	reader.onload = () => {
		const image = new Image();
		image.onload = () => {
			const canvas = canvasEl.value;
			const ctx = context();
			if (!canvas || !ctx) return;
			wipe();
			const boxWidth = canvas.width / ratio();
			const boxHeight = canvas.height / ratio();
			// contain, so a wide or tall scan keeps its proportions
			const scale = Math.min(boxWidth / image.width, boxHeight / image.height, 1);
			const drawWidth = image.width * scale;
			const drawHeight = image.height * scale;
			ctx.drawImage(
				image,
				(boxWidth - drawWidth) / 2,
				(boxHeight - drawHeight) / 2,
				drawWidth,
				drawHeight
			);
			hasInk.value = true;
			emitImage();
		};
		image.src = String(reader.result);
	};
	reader.readAsDataURL(file);
}

// —— exporting ——
//
// What leaves this component is the signature, not the pad it was drawn on. The
// canvas is mostly empty space, so an untrimmed export carries the ink floating
// somewhere inside a large transparent box. Cropping to the ink makes the stored
// image the signature itself, at the width the print format draws it.

const EXPORT_WIDTH = 160;
const EXPORT_HEIGHT = 60;
/** Dots per displayed pixel, so the signature survives zooming and printing. */
const EXPORT_PIXEL_RATIO = 3;
/** Blank margin kept around the ink, in CSS pixels. */
const EXPORT_PADDING = 4;

type Box = { left: number; top: number; right: number; bottom: number };

/** The smallest box containing every drawn pixel, in canvas pixels. */
function inkBox(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement): Box | null {
	const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
	let left = canvas.width;
	let top = canvas.height;
	let right = -1;
	let bottom = -1;

	for (let y = 0; y < canvas.height; y++) {
		for (let x = 0; x < canvas.width; x++) {
			// alpha only: the ink is opaque and everything else was never painted
			if (!data[(y * canvas.width + x) * 4 + 3]) continue;
			if (x < left) left = x;
			if (x > right) right = x;
			if (y < top) top = y;
			if (y > bottom) bottom = y;
		}
	}

	return right < 0 ? null : { left, top, right, bottom };
}

/** The ink alone, padded and scaled to print size. Empty string if nothing is drawn. */
function exportImage(): string {
	const canvas = canvasEl.value;
	const ctx = context();
	const box = canvas && ctx ? inkBox(ctx, canvas) : null;
	if (!canvas || !ctx || !box) return "";

	const pad = Math.round(EXPORT_PADDING * ratio());
	const x = Math.max(0, box.left - pad);
	const y = Math.max(0, box.top - pad);
	const width = Math.min(canvas.width, box.right + pad + 1) - x;
	const height = Math.min(canvas.height, box.bottom + pad + 1) - y;

	// bounded on both sides, so a tall signature is no bigger than a wide one;
	// never upscaled, because a small scribble has no detail to invent
	const scale = Math.min(
		(EXPORT_WIDTH * EXPORT_PIXEL_RATIO) / width,
		(EXPORT_HEIGHT * EXPORT_PIXEL_RATIO) / height,
		1
	);

	const out = document.createElement("canvas");
	out.width = Math.max(1, Math.round(width * scale));
	out.height = Math.max(1, Math.round(height * scale));
	const outCtx = out.getContext("2d");
	if (!outCtx) return "";
	outCtx.drawImage(canvas, x, y, width, height, 0, 0, out.width, out.height);
	return out.toDataURL("image/png");
}

function emitImage() {
	if (!hasInk.value) return emit("update:modelValue", "");
	emit("update:modelValue", exportImage());
}

function clear() {
	wipe();
	hasInk.value = false;
	if (fileEl.value) fileEl.value.value = "";
	emit("update:modelValue", "");
}

/**
 * Resizing the canvas resets its backing store, so the drawing has to be put
 * back. Ignore resizes that don't actually change the size — a plain resize
 * event would otherwise wipe a signature someone had already drawn.
 */
function onWindowResize() {
	const canvas = canvasEl.value;
	if (!canvas) return;
	const rect = canvas.getBoundingClientRect();
	if (Math.round(rect.width * ratio()) === canvas.width) return;

	const previousImage = hasInk.value ? canvas.toDataURL("image/png") : "";
	resize();
	if (!previousImage) return;

	const image = new Image();
	image.onload = () => {
		const ctx = context();
		if (!ctx) return;
		ctx.drawImage(image, 0, 0, canvas.width / ratio(), canvas.height / ratio());
	};
	image.src = previousImage;
}

onMounted(() => {
	resize();
	if (typeof window !== "undefined") window.addEventListener("resize", onWindowResize);
});

onBeforeUnmount(() => {
	if (typeof window !== "undefined") window.removeEventListener("resize", onWindowResize);
});

// switching tabs starts a fresh signature; Load opens the picker straight away
watch(mode, (next) => {
	clear();
	if (next === "load") fileEl.value?.click();
});
</script>
