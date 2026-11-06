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
		<!-- a document page in the side-panel layout: the note and item table, then the facts beside them
		     on a wide screen (below it, under them), as `.portal-doc` lays the page out -->
		<div v-else-if="variant === 'detail'" class="portal-doc">
			<div class="portal-doc-lead">
				<div class="flex w-full flex-col">
					<Skeleton :class="[BLOCK, 'mb-6 h-11 w-full rounded']" />
					<Line text="text-lg-semibold" width="9rem" />
					<div
						class="mt-3 grid h-8 items-center gap-3.5 px-3"
						:style="{ gridTemplateColumns: columns.join(' ') }"
					>
						<Line text="text-sm" width="1rem" end />
						<Line text="text-sm" width="2rem" />
						<Line v-for="c in columns.length - 2" :key="c" text="text-sm" width="3rem" end />
					</div>
					<div
						v-for="i in 2"
						:key="i"
						class="grid items-start gap-3.5 border-b border-outline-gray-1 px-3 py-3"
						:style="{ gridTemplateColumns: columns.join(' ') }"
					>
						<Line text="text-sm" width="0.5rem" end />
						<div class="flex min-w-0 items-start gap-2.5">
							<Skeleton :class="[BLOCK, 'size-8 shrink-0 rounded']" />
							<div class="flex min-w-0 flex-1 flex-col gap-0.5">
								<Line text="text-base-medium" :width="width(i, 30)" />
								<Line text="text-p-sm" :width="width(i + 2, 45)" />
							</div>
						</div>
						<Line
							v-for="c in columns.length - 2"
							:key="c"
							text="text-base"
							:width="c === 1 ? '60%' : '75%'"
							end
						/>
					</div>
					<!-- the total, at the right edge -->
					<div class="ml-auto w-48 pt-4">
						<Line text="text-p-base" width="100%" />
					</div>
				</div>
			</div>
			<div class="portal-doc-aside flex flex-col gap-6">
				<div class="flex w-full flex-col gap-3">
					<Line text="text-sm" width="3rem" />
					<div v-for="i in 4" :key="i" class="flex justify-between gap-3">
						<Line text="text-base" width="5rem" />
						<Line text="text-base" width="6rem" end />
					</div>
				</div>
				<div class="flex w-full flex-col gap-1 border-t border-outline-gray-1 pt-6">
					<Line text="text-sm" width="6rem" />
					<Line text="text-base-semibold" width="60%" />
					<Line text="text-p-sm" width="90%" />
					<Line text="text-p-sm" width="70%" />
				</div>
			</div>
		</div>

		<!-- home: the company, the four counters, and the first rows of two document groups -->
		<div v-else-if="variant === 'home'" class="mx-auto flex max-w-[900px] flex-col gap-6">
			<div class="flex flex-col gap-4">
				<Line text="text-3xl-semibold" width="12rem" />
				<div class="grid gap-3" style="grid-template-columns: repeat(auto-fit, minmax(170px, 1fr))">
					<div
						v-for="i in 4"
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
@media (prefers-reduced-motion: reduce) {
	.portal-skeleton,
	.portal-reveal {
		animation: none;
	}
}
/* A document page: the items lead, the facts sit in a side panel on the right, and everything longer
   (terms, payments, comments) follows the items. The panel only sits beside the items on a wide
   screen, where the item table still has room; narrower, it is one column in the same order. Studio
   blocks have no wide-screen breakpoint, so the layout lives here. */
.portal-doc {
	display: grid;
	grid-template-columns: minmax(0, 1fr);
}
.portal-doc-lead,
.portal-doc-rest {
	padding: 24px 24px 0;
}
.portal-doc-rest {
	padding-top: 32px;
	padding-bottom: 64px;
	border-top: 1px solid var(--outline-gray-1);
}
.portal-doc-lead > *,
.portal-doc-rest > * {
	width: 100%;
	max-width: 880px;
	margin-inline: auto;
}
.portal-doc-aside {
	margin-top: 32px;
	padding: 0 24px 32px;
	border-top: 1px solid var(--outline-gray-1);
}
.portal-doc-aside > * {
	max-width: 880px;
	margin-inline: auto;
}
/* as a desk form's sidebar: every section gets the same 20px above and below, with a line between */
.portal-side-section {
	padding-block: 20px;
}
.portal-side-section + .portal-side-section {
	border-top: 1px solid var(--outline-gray-1);
}
@media (max-width: 767px) {
	.portal-doc-lead,
	.portal-doc-rest,
	.portal-doc-aside {
		padding-inline: 12px;
	}
}
@media (min-width: 1280px) {
	.portal-doc {
		grid-template-columns: minmax(0, 1fr) 20rem;
		grid-template-rows: auto 1fr;
		min-height: 100%;
	}
	.portal-doc-lead {
		grid-column: 1;
		grid-row: 1;
	}
	.portal-doc-rest {
		grid-column: 1;
		grid-row: 2;
		border-top: 0;
	}
	.portal-doc-aside {
		grid-column: 2;
		grid-row: 1 / span 2;
		margin-top: 0;
		padding: 0 0 40px;
		border-top: 0;
		border-left: 1px solid var(--outline-gray-1);
		align-self: stretch;
	}
	.portal-doc-aside > * {
		max-width: none;
	}
	/* the side padding sits on each section, so the lines between them run edge to edge */
	.portal-doc-aside > .portal-side-section {
		padding-inline: 20px;
	}
}
/* The status note, as the design's strip: tinted by its theme, body weight, and wrapping rather than
   cut off. frappe-ui's Alert draws a grey box with a medium, one-line title. */
.portal-doc-lead [data-slot="title"],
.portal-notice [data-slot="title"] {
	font-weight: 420;
	white-space: normal;
	line-height: 1.5;
}
.portal-doc-lead [role][data-layout="row"],
.portal-notice[data-layout="row"] {
	height: auto;
	min-height: 2.5rem;
}
.portal-doc-lead [data-color="blue"] {
	background: var(--surface-blue-2);
}
.portal-doc-lead [data-color="green"] {
	background: var(--surface-green-2);
}
.portal-doc-lead [data-color="amber"],
.portal-notice[data-color="amber"] {
	background: var(--surface-amber-2);
}
.portal-doc-lead [data-color="red"] {
	background: var(--surface-red-2);
}
/* Shown or hidden at the width where the side panel sits beside the items: Print moves from the
   page header to the top of the panel, as on a desk form. */
.portal-xl-only {
	display: none !important;
}
@media (min-width: 1280px) {
	.portal-xl-only {
		display: inline-flex !important;
	}
	.portal-below-xl {
		display: none !important;
	}
}
/* on a phone the quieter answer folds into the header's menu */
@media (max-width: 639px) {
	.portal-sm-up {
		display: none !important;
	}
}
@media (prefers-reduced-motion: reduce) {
	.portal-skeleton,
	.portal-reveal {
		animation: none;
	}
}
</style>
