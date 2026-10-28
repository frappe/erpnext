<script setup>
import { computed } from "vue";
import { Alert, Badge, Button, Progress, Tooltip } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";
import { useHost } from "@framework/ui/island";

import FigureRows from "./FigureRows.vue";
import { form_route } from "../costing.js";
import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();
const host = useHost();

const INVOICE_THEMES = {
	Paid: "green",
	Unpaid: "amber",
	"Partly Paid": "amber",
	Overdue: "red",
	Return: "gray",
};
const ORDER_THEMES = { "To Bill": "blue", "To Deliver and Bill": "blue", Completed: "green", Closed: "gray" };

const billing = computed(() => props.view.billing);
const orders = computed(() => billing.value.sales_orders || []);

// A customer project with nothing ordered or billed yet.
const not_started = computed(() => !props.view.has_contract && !props.view.billed);
const show_orders = computed(() => orders.value.length > 1 || billing.value.closed_remainder > 0);

const rows = computed(() => {
	const view = props.view;
	const out = [];
	if (view.has_contract)
		out.push({
			label: __("Contract value"),
			value: format.short(view.contract),
		});
	out.push({
		label: __("Billed to date"),
		caption: __("Invoices, net of returns"),
		value: format.short(view.billed),
	});
	if (view.has_contract && !billing.value.over_billed) out.push(left_to_bill_row());
	if (billing.value.closed_remainder)
		out.push({
			label: __("Not billable"),
			caption: __("Unbilled part of a closed order"),
			value: format.short(billing.value.closed_remainder),
			tone: "text-ink-gray-4",
		});
	// Each of these is null when the user may not read the documents behind it.
	if (billing.value.outstanding != null)
		out.push({
			label: __("Outstanding"),
			caption: __("Invoiced, unpaid"),
			value: format.short(billing.value.outstanding),
			tone: billing.value.overdue ? "text-ink-red-5" : "",
		});
	if (billing.value.unbilled)
		out.push({
			label: view.has_contract ? __("Unbilled timesheets") : __("Ready to bill"),
			caption: __("Billable hours, not invoiced"),
			value: format.short(billing.value.unbilled.amount, billing.value.unbilled.currency),
		});
	return out;
});

// The rows show label and amount only. What each one counts is in the tooltip by the title.
const figures = computed(() => rows.value.map(({ caption, ...figure }) => figure));
const definitions = computed(() =>
	rows.value
		.filter((row) => row.caption)
		.map((row) => `${row.label}: ${row.caption}`)
		.join(" · ")
);

function left_to_bill_row() {
	const left = billing.value.left_to_bill;
	if (props.view.phase === "cancelled")
		return {
			label: __("Not billable"),
			value: format.short(left),
			tone: "text-ink-gray-4",
		};
	if (props.view.phase === "completed")
		return {
			label: __("Never billed"),
			value: format.short(left),
			tone: left > 0 ? "text-ink-amber-5" : "",
		};
	return { label: __("Left to bill"), value: format.short(left) };
}

function create(doctype) {
	const options = new URLSearchParams({ project: props.view.project, customer: props.view.customer || "" });
	host.navigate?.(`Form/${doctype}/new?${options}`);
}
const open = (doctype, name) => host.navigate?.(form_route(doctype, name));
</script>

<template>
	<ChartCard>
		<ChartContainer :title="__('Billing')">
			<template v-if="definitions && !not_started" #title-suffix>
				<Tooltip :text="definitions">
					<span
						class="lucide-info size-[1em] text-ink-gray-4"
						role="img"
						:aria-label="definitions"
					/>
				</Tooltip>
			</template>
			<template v-if="view.access.invoices && !not_started && !view.closed" #actions>
				<Button
					size="sm"
					:label="__('Create invoice')"
					icon-left="lucide-plus"
					@click="create('Sales Invoice')"
				/>
			</template>

			<div class="space-y-4 pt-2">
				<div
					v-if="not_started"
					class="flex flex-col items-center justify-center gap-3 py-10 text-center"
				>
					<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
						<span class="lucide-file-text size-6" aria-hidden="true" />
					</div>
					<p class="text-base text-ink-gray-7">{{ __("Not billed yet") }}</p>
					<div v-if="!view.closed" class="mt-2 flex flex-wrap justify-center gap-2">
						<Button
							v-if="view.access.sales_orders"
							variant="solid"
							theme="gray"
							:label="__('Create sales order')"
							@click="create('Sales Order')"
						/>
						<Button
							v-if="view.access.invoices"
							variant="ghost"
							:label="__('Create invoice')"
							@click="create('Sales Invoice')"
						/>
					</div>
				</div>

				<template v-else>
					<Progress
						v-if="view.has_contract"
						:value="Math.min(view.billed_percent, 100)"
						:label="
							__('{0} billed of {1} · {2}', [
								format.short(view.billed),
								format.short(view.contract),
								format.percent(view.billed_percent),
							])
						"
						size="md"
					/>
					<Alert
						v-if="billing.over_billed"
						theme="amber"
						:title="__('{0} billed beyond the sales orders', [format.short(billing.over_billed)])"
						:description="__('Amend the sales order, or check for duplicate invoices.')"
					/>
					<FigureRows :rows="figures" />

					<List v-if="show_orders" :columns="['minmax(0,1fr)', '5rem', '8.5rem']" :row-height="48">
						<ListHeader>
							<ListHeaderCell>{{ __("Sales order") }}</ListHeaderCell>
							<ListHeaderCell class="justify-end">{{ __("Amount") }}</ListHeaderCell>
							<ListHeaderCell class="justify-end">{{ __("Status") }}</ListHeaderCell>
						</ListHeader>
						<ListRow
							v-for="order in orders"
							:key="order.name"
							@click="open('Sales Order', order.name)"
						>
							<ListCell>
								<div class="min-w-0">
									<p class="truncate text-sm text-ink-gray-8">{{ order.name }}</p>
									<p class="truncate text-xs text-ink-gray-5">
										{{ format.date(order.transaction_date) }}
									</p>
								</div>
							</ListCell>
							<ListCell class="justify-end">
								<div class="text-right">
									<p class="text-sm tabular-nums text-ink-gray-8">
										{{ format.short(order.base_net_total) }}
									</p>
									<p class="text-xs tabular-nums text-ink-gray-5">
										{{ __("{0} billed", [format.percent(order.per_billed)]) }}
									</p>
								</div>
							</ListCell>
							<ListCell class="justify-end">
								<Badge
									:label="__(order.status)"
									:theme="ORDER_THEMES[order.status] || 'gray'"
									variant="subtle"
								/>
							</ListCell>
						</ListRow>
					</List>

					<List
						v-if="billing.invoices?.length"
						:columns="['minmax(0,1fr)', '5rem', '6rem']"
						:row-height="48"
					>
						<ListHeader>
							<ListHeaderCell>{{ __("Sales invoice") }}</ListHeaderCell>
							<ListHeaderCell class="justify-end">{{ __("Amount") }}</ListHeaderCell>
							<ListHeaderCell class="justify-end">{{ __("Status") }}</ListHeaderCell>
						</ListHeader>
						<ListRow
							v-for="invoice in billing.invoices"
							:key="invoice.name"
							@click="open('Sales Invoice', invoice.name)"
						>
							<ListCell>
								<div class="min-w-0">
									<p class="truncate text-sm text-ink-gray-8">{{ invoice.name }}</p>
									<p class="truncate text-xs text-ink-gray-5">
										{{ format.date(invoice.posting_date) }}
									</p>
								</div>
							</ListCell>
							<ListCell class="justify-end">
								<span
									class="text-sm tabular-nums"
									:class="invoice.amount < 0 ? 'text-ink-gray-5' : 'text-ink-gray-8'"
								>
									{{ format.short(invoice.amount) }}
								</span>
							</ListCell>
							<ListCell class="justify-end">
								<Badge
									:label="__(invoice.status)"
									:theme="INVOICE_THEMES[invoice.status] || 'gray'"
									variant="subtle"
								/>
							</ListCell>
						</ListRow>
					</List>
				</template>
			</div>
		</ChartContainer>
	</ChartCard>
</template>
