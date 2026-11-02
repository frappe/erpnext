<template>
	<!-- one root element: Studio drops a block's styles on a fragment root -->
	<div :class="['w-full', !bare && 'portal-skeleton']" :aria-busy="bare ? undefined : 'true'">
		<span v-if="!bare" class="sr-only" role="status">{{ __("Loading") }}</span>

		<!-- a list page's rows, in the List's own columns and 60px rows; the List's header stays above -->
		<div v-if="variant === 'list'" class="-mx-3">
			<div
				v-for="i in count"
				:key="i"
				class="grid h-[60px] items-center gap-2 px-3"
				:style="{ gridTemplateColumns: columns.join(' ') }"
			>
				<div v-for="(_, c) in columns" :key="c" class="flex min-w-0 flex-col gap-1.5">
					<template v-if="c === 0">
						<Line text="text-base-medium" :width="width(i, 45)" />
						<Line text="text-sm" :width="width(i + 3, 30)" />
					</template>
					<Skeleton
						v-else-if="c === columns.length - 2"
						:class="[BLOCK, 'h-5 w-20 rounded-full']"
					/>
					<Line v-else-if="c === columns.length - 1" text="text-base" width="70%" end />
					<Line v-else text="text-sm" :width="width(i + c, 50)" />
				</div>
			</div>
		</div>

		<!-- a document page: the info and address columns, the item table and its total -->
		<div v-else-if="variant === 'detail'" class="mx-auto flex max-w-[900px] flex-col gap-6">
			<div class="grid grid-cols-3 gap-8">
				<div class="flex min-w-0 flex-col gap-3">
					<Line text="text-sm-medium" width="2.5rem" />
					<div
						class="grid gap-x-4 gap-y-2.5"
						style="grid-template-columns: max-content minmax(0, 1fr)"
					>
						<template v-for="i in 4" :key="i">
							<Line text="text-p-sm" width="3rem" />
							<Line text="text-p-base" :width="width(i, 50)" />
						</template>
					</div>
				</div>
				<div v-for="column in 2" :key="column" class="flex min-w-0 flex-col gap-3">
					<Line text="text-sm-medium" width="7rem" />
					<div class="flex flex-col gap-1">
						<Line text="text-p-base" width="60%" />
						<Line text="text-p-base" width="90%" />
						<Line text="text-p-base" width="50%" />
					</div>
				</div>
			</div>

			<div class="flex flex-col">
				<div
					class="grid h-8 items-center gap-3.5"
					:style="{ gridTemplateColumns: columns.join(' ') }"
				>
					<Line text="text-sm" width="2rem" />
					<Line v-for="c in columns.length - 1" :key="c" text="text-sm" width="3rem" end />
				</div>
				<div
					v-for="i in 2"
					:key="i"
					class="grid h-[62px] items-center gap-3.5"
					:style="{ gridTemplateColumns: columns.join(' ') }"
				>
					<div class="flex min-w-0 items-center gap-2.5">
						<Skeleton :class="[BLOCK, 'size-8 shrink-0 rounded']" />
						<div class="flex min-w-0 flex-1 flex-col gap-0.5">
							<Line text="text-base-medium" :width="width(i, 30)" />
							<Line text="text-p-sm" :width="width(i + 2, 45)" />
						</div>
					</div>
					<Line
						v-for="c in columns.length - 1"
						:key="c"
						text="text-base"
						:width="c === 1 ? '60%' : '75%'"
						end
					/>
				</div>
				<div class="border-t border-outline-gray-1 pt-2.5">
					<Line text="text-p-base" width="12rem" end />
				</div>
			</div>
		</div>

		<!-- home: the company, the three counters, and the first rows of two document groups -->
		<div v-else-if="variant === 'home'" class="mx-auto flex max-w-[900px] flex-col gap-6">
			<div class="flex flex-col gap-4">
				<Line text="text-3xl-semibold" width="12rem" />
				<div class="grid gap-3" style="grid-template-columns: repeat(auto-fit, minmax(170px, 1fr))">
					<div
						v-for="i in 3"
						:key="i"
						class="flex h-[100px] flex-col gap-1.5 rounded-4 border border-outline-gray-1 px-4 py-3"
					>
						<Line text="text-sm" :width="width(i, 60)" />
						<Line text="text-3xl-semibold" width="35%" />
						<Line text="text-sm" :width="width(i + 4, 55)" />
					</div>
				</div>
			</div>
			<div v-for="group in 2" :key="group" class="flex flex-col gap-2">
				<div class="flex h-7 items-center justify-between">
					<Line text="text-lg-semibold w-24" width="100%" />
					<Line text="text-base w-20" width="100%" />
				</div>
				<PortalSkeleton variant="list" :count="3" bare />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { h, type FunctionalComponent } from "vue";
import { Skeleton } from "frappe-ui";
import { __ } from "@app/lib/translate";

defineOptions({ name: "PortalSkeleton" });

withDefaults(
	defineProps<{
		variant?: "list" | "detail" | "home";
		/** Rows of a list: what the page showed last time, so the page does not jump when they arrive. */
		count?: number;
		/** The grid columns of the list, or of a document's item table, the same ones its List block uses. */
		columns?: string[];
		/** Nested inside another skeleton, which already announces loading and fades in. */
		bare?: boolean;
	}>(),
	{ variant: "list", count: 8, columns: () => ["minmax(0, 1fr)", "13rem", "7.5rem", "8rem"] }
);

const BLOCK = "motion-reduce:animate-none";

// varied, so the rows read as text rather than as a grid of bars
const WIDTHS = [72, 58, 84, 64, 90, 52, 78, 68];
function width(index: number, floor: number) {
	return `${Math.max(WIDTHS[index % WIDTHS.length], floor)}%`;
}

/** A bar inside a line of the text it stands in for: the text style gives the height, so swapping in
 *  the real text moves nothing. */
const Line: FunctionalComponent<{ text: string; width: string; end?: boolean }> = (props) =>
	h("div", { class: ["relative", props.text] }, [
		// non-breaking: a plain space alone collapses, and the line would have no height
		"\u00a0",
		h(Skeleton, {
			// `end` for a right-aligned column, such as an amount
			class: [
				BLOCK,
				props.end ? "end-0" : "start-0",
				"absolute top-1/2 h-[0.6em] -translate-y-1/2 rounded-full",
			],
			style: { width: props.width },
		}),
	]);
Line.props = ["text", "width", "end"];
</script>

<style>
/* `backwards`, not `both`: a held opacity fill would keep a dialog under its backdrop. Held back a
   moment, so a fast load swaps straight to the page with no flash of grey. */
.portal-skeleton {
	animation: portal-fade-in 200ms ease-out 150ms backwards;
}
/* on the page content that replaces a skeleton, so it eases in rather than popping */
.portal-reveal {
	animation: portal-fade-in 180ms ease-out backwards;
}
@keyframes portal-fade-in {
	from {
		opacity: 0;
	}
}
/* Printing a page (an RFQ, a receipt): the document only, without the sidebar, buttons or comment
   box, and every row of it rather than the screen's scrolled window. The pages mark what to leave
   out with `portal-no-print`; this is the app's one global stylesheet, so the rule lives here. */
@media print {
	.portal-no-print {
		display: none !important;
	}
	html,
	body,
	#app,
	.portal-print-page,
	.portal-print-page * {
		height: auto !important;
		max-height: none !important;
		overflow: visible !important;
	}
	.portal-reveal {
		animation: none;
	}
}
@media (prefers-reduced-motion: reduce) {
	.portal-skeleton,
	.portal-reveal {
		animation: none;
	}
}
</style>
