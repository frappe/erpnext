<script setup>
import { computed, ref } from "vue";
import { Alert, Button, Dropdown, ErrorMessage, Skeleton, TabButtons } from "frappe-ui";
import { useHost } from "@framework/ui/island";

import AccountsView from "./components/AccountsView.vue";
import BillingCard from "./components/BillingCard.vue";
import EstimateCard from "./components/EstimateCard.vue";
import CostBreakdown from "./components/CostBreakdown.vue";
import CostDrivers from "./components/CostDrivers.vue";
import CostTrend from "./components/CostTrend.vue";
import KpiCards from "./components/KpiCards.vue";
import { accountsReports } from "./accounts.js";
import { hiddenFor } from "./alerts.js";
import { report_route, toView } from "./costing.js";
import { createFormat, provideFormat } from "./format.js";
import { kpisFor } from "./kpis.js";
import { useProjectAccounts, useProjectCosting } from "./useProjectCosting.js";

// What a Vue Component field passes: the form's document, as it stands.
const props = defineProps({
	doctype: { type: String, default: "Project" },
	name: { type: String, default: null },
	doc: { type: Object, default: () => ({}) },
	is_new: { type: Boolean, default: false },
	read_only: { type: Boolean, default: false },
});

const __ = window.__;
const host = useHost();
const element = ref(null);
const mode = ref("project");
const modes = [
	{ value: "project", label: __("Project cost") },
	{ value: "accounts", label: __("Accounts") },
];

const costing = useProjectCosting(
	element,
	() => props.name,
	() => props.doc.modified
);
const accounts = useProjectAccounts(
	element,
	() => props.name,
	() => props.doc.modified,
	() => mode.value === "accounts"
);
const view = computed(() => (costing.data?.summary ? toView(costing.data, props.doc) : null));
const format = createFormat(host, () => costing.data?.currency);
provideFormat(format);

const kpis = computed(() => kpisFor(view.value, format));
const hidden = computed(() => {
	if (mode.value === "project") return hiddenFor(view.value);
	return accounts.data && !accounts.data.access.budgets ? [__("Budget records")] : [];
});
const failed = computed(() => mode.value === "project" && Object.keys(costing.data?.errors || {}).length > 0);
// Only a viewer who may read the ledger gets the Accounts view.
const has_accounts = computed(() => Boolean(view.value?.access.ledger));

// Each mode offers the reports behind its own numbers, those the site has and the user may open.
const reports = computed(() => {
	const items =
		mode.value === "accounts"
			? accounts.data && accountsReports(accounts.data)
			: costing.data?.reports?.map((report) => [
					__(report.name),
					report_route(report.name, report.filters),
			  ]);
	return (items || []).map(([label, route]) => ({ label, onClick: () => host.navigate?.(route) }));
});

function new_timesheet() {
	host.navigate?.(`Form/Timesheet/new?parent_project=${encodeURIComponent(props.name)}`);
}
</script>

<template>
	<div ref="element" class="space-y-5 pb-8 pt-2">
		<template v-if="!is_new">
			<div class="flex flex-wrap items-center gap-3">
				<TabButtons v-if="has_accounts" v-model="mode" :options="modes" size="sm" />
				<div v-if="reports.length" class="ml-auto">
					<Dropdown :options="reports">
						<Button size="sm" :label="__('Reports')" icon-right="lucide-chevron-down" />
					</Dropdown>
				</div>
			</div>

			<Alert
				v-if="costing.error"
				theme="red"
				:title="__('Could not load the costing')"
				:primary-action="{ label: __('Try again'), onClick: () => costing.reload() }"
				:description="costing.error.message"
			/>

			<template v-else-if="mode === 'accounts'">
				<Alert
					v-if="accounts.error"
					theme="red"
					:title="__('Could not load the accounts')"
					:primary-action="{ label: __('Try again'), onClick: () => accounts.reload() }"
					:description="accounts.error.message"
				/>
				<AccountsView
					v-else-if="accounts.data"
					:payload="accounts.data"
					:closed="view.closed"
					:has_labour="view.sources.some((source) => source.key === 'labour' && source.amount)"
				/>
				<div v-else class="space-y-5">
					<div class="grid grid-cols-2 gap-5 lg:grid-cols-4">
						<Skeleton v-for="index in 4" :key="index" class="h-24 w-full rounded-4" />
					</div>
					<Skeleton class="h-80 w-full rounded-4" />
				</div>
			</template>

			<div v-else-if="!view" class="space-y-5">
				<div class="grid grid-cols-2 gap-5 lg:grid-cols-4">
					<Skeleton v-for="index in 4" :key="index" class="h-24 w-full rounded-4" />
				</div>
				<Skeleton class="h-80 w-full rounded-4" />
			</div>

			<div
				v-else-if="view.health === 'empty'"
				class="flex flex-col items-center justify-center gap-3 py-16 text-center"
			>
				<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
					<span class="lucide-receipt size-6" aria-hidden="true" />
				</div>
				<p class="text-base text-ink-gray-7">{{ __("No costs booked yet") }}</p>
				<Button
					v-if="!view.closed"
					variant="solid"
					theme="gray"
					icon-left="lucide-clock"
					:label="__('Log time')"
					class="mt-2"
					@click="new_timesheet"
				/>
			</div>

			<template v-else>
				<KpiCards :items="kpis" />
				<div class="grid gap-5 lg:grid-cols-5">
					<EstimateCard class="lg:col-span-2" :view="view" />
					<CostTrend class="lg:col-span-3" :view="view" />
				</div>
				<div class="grid gap-5 lg:grid-cols-2">
					<CostBreakdown :view="view" />
					<CostDrivers v-if="view.drivers" :view="view" />
				</div>
				<BillingCard v-if="!view.internal && view.billing" :view="view" />
			</template>

			<ErrorMessage
				v-if="failed"
				class="text-center"
				:message="__('Some sections could not be calculated. The error is in the Error Log.')"
			/>
			<p v-if="hidden.length" class="text-center text-p-xs text-ink-gray-5">
				{{ __("Hidden by your permissions: {0}.", [hidden.join(", ")]) }}
			</p>
		</template>
	</div>
</template>
