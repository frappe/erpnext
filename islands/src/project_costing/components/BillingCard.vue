<script setup>
import { computed, ref } from "vue";
import { Badge, Button, Progress, TabButtons } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";
import { useHost } from "@framework/ui/island";

import { form_route, list_route } from "../costing.js";
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
// Shared by the order and invoice lists, so their columns line up.
const LIST_COLUMNS = ["minmax(0,1fr)", "6rem", "7.5rem"];
const ORDER_THEMES = { "To Bill": "blue", "To Deliver and Bill": "blue", Completed: "green", Closed: "gray" };

const billing = computed(() => props.view.billing);
const orders = computed(() => billing.value.sales_orders || []);

// Each list shows the newest few; past that, a link opens the desk list filtered to the project.
// Without an invoice filter, the project's invoices are too many and too mixed to link to.
const more = computed(() => {
	const order_count = billing.value.sales_order_count;
	const invoice_count = billing.value.invoice_count;
	return {
		orders:
			order_count > orders.value.length
				? more_link("Sales Order", __("View all {0} sales orders", [order_count]))
				: null,
		invoices:
			invoice_count > (billing.value.invoices?.length || 0) && billing.value.invoice_filter
				? more_link(
						"Sales Invoice",
						__("View all {0} sales invoices", [invoice_count]),
						billing.value.invoice_filter
				  )
				: null,
	};
});

// Orders name the project on themselves; invoices may name it only on their items, so the server
// says how to find them.
const more_link = (doctype, label, filter = { project: props.view.project }) => ({
	label,
	route: list_route(doctype, { ...filter, docstatus: 1 }),
});

// A customer project with nothing ordered or billed yet.
const not_started = computed(() => !props.view.has_contract && !props.view.billed);
// One list at a time, invoices first: their payment status is what needs acting on.
const list_tabs = computed(() => [
	...(billing.value.invoices?.length
		? [{ value: "invoices", label: __("Invoices · {0}", [billing.value.invoice_count]) }]
		: []),
	...(orders.value.length
		? [{ value: "orders", label: __("Sales orders · {0}", [billing.value.sales_order_count]) }]
		: []),
]);
const list_tab = ref("invoices");
const active_list = computed(() =>
	list_tabs.value.some((tab) => tab.value === list_tab.value) ? list_tab.value : list_tabs.value[0]?.value
);

// Without a sales order there is no bar to measure against, so the line is what was billed.
const summary = computed(() =>
	props.view.has_contract
		? __("{0} billed of {1} · {2}", [
				format.money(props.view.billed),
				format.money(props.view.contract),
				format.percent(props.view.billed_percent),
		  ])
		: __("{0} billed", [format.money(props.view.billed)])
);

function create(doctype) {
	const options = new URLSearchParams({ project: props.view.project, customer: props.view.customer || "" });
	host.navigate?.(`Form/${doctype}/new?${options}`);
}
const open = (doctype, name) => host.navigate?.(form_route(doctype, name));
</script>

<template>
	<ChartCard>
		<ChartContainer :title="__('Billing')">
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

				<!-- Read top to bottom: what is billed, then one list of the documents behind it. -->
				<template v-else>
					<Progress
						v-if="view.has_contract"
						:value="Math.min(view.billed_percent, 100)"
						:label="summary"
						size="md"
					/>
					<p v-else class="text-base-medium text-ink-gray-8">{{ summary }}</p>
					<TabButtons
						v-if="list_tabs.length > 1"
						v-model="list_tab"
						:options="list_tabs"
						size="sm"
					/>
					<List v-if="active_list === 'invoices'" :columns="LIST_COLUMNS" :row-height="48">
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
									{{ format.money(invoice.amount) }}
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
					<Button
						v-if="active_list === 'invoices' && more.invoices"
						variant="ghost"
						size="sm"
						icon-right="lucide-arrow-up-right"
						:label="more.invoices.label"
						@click="host.navigate?.(more.invoices.route)"
					/>
					<List v-if="active_list === 'orders'" :columns="LIST_COLUMNS" :row-height="48">
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
										{{ format.money(order.base_net_total) }}
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
					<Button
						v-if="active_list === 'orders' && more.orders"
						variant="ghost"
						size="sm"
						icon-right="lucide-arrow-up-right"
						:label="more.orders.label"
						@click="host.navigate?.(more.orders.route)"
					/>
				</template>
			</div>
		</ChartContainer>
	</ChartCard>
</template>
