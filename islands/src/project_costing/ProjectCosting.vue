<script setup>
import { computed, ref } from "vue";
import { Alert, Button, Dropdown, ErrorMessage, Skeleton, Tooltip } from "frappe-ui";
import { NumberCard } from "frappe-ui/charts";
import { useHost } from "@framework/ui/island";

import BillingCard from "./components/BillingCard.vue";
import BudgetCard from "./components/BudgetCard.vue";
import CostBreakdown from "./components/CostBreakdown.vue";
import CostDrivers from "./components/CostDrivers.vue";
import CostTrend from "./components/CostTrend.vue";
import MarginCard from "./components/MarginCard.vue";
import RateGapsDialog from "./components/RateGapsDialog.vue";
import { alertFor, hiddenFor } from "./alerts.js";
import { toView } from "./costing.js";
import { createFormat, provideFormat } from "./format.js";
import { kpisFor } from "./kpis.js";
import { useProjectCosting } from "./useProjectCosting.js";

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
const show_rate_gaps = ref(false);

const costing = useProjectCosting(
	element,
	() => props.name,
	() => props.doc.modified
);
const view = computed(() => (costing.data?.summary ? toView(costing.data, props.doc) : null));
const format = createFormat(host, () => costing.data?.currency);
provideFormat(format);

const kpis = computed(() => kpisFor(view.value, format));
const alert = computed(() =>
	alertFor(view.value, format, { fix_rates: () => (show_rate_gaps.value = true) })
);
const hidden = computed(() => hiddenFor(view.value));
const failed = computed(() => Object.keys(costing.data?.errors || {}).length > 0);

const context = computed(() =>
	view.value?.hrms
		? __("Measured from timesheets, purchase invoices, stock consumption and expense claims.")
		: __("Measured from timesheets, purchase invoices and stock consumption.")
);

const reports = computed(() =>
	["Project Profitability", "Project Billing Summary", "Timesheet Billing Summary"].map((report) => ({
		label: __(report),
		onClick: () => host.navigate?.(`query-report/${report}?project=${encodeURIComponent(props.name)}`),
	}))
);

function new_timesheet() {
	host.navigate?.(`Form/Timesheet/new?parent_project=${encodeURIComponent(props.name)}`);
}
</script>

<template>
	<div ref="element" class="space-y-5 pb-8 pt-2">
		<template v-if="!is_new">
			<div class="flex flex-wrap items-center gap-2">
				<p class="text-p-sm text-ink-gray-5">{{ context }}</p>
				<div class="ml-auto">
					<Dropdown :options="reports">
						<Button size="sm" :label="__('Reports')" icon-right="lucide-chevron-down" />
					</Dropdown>
				</div>
			</div>

			<Alert
				v-if="costing.error"
				theme="red"
				:title="__('Could not load the costing')"
				:description="costing.error.message"
			/>

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
				<p class="max-w-md text-p-sm text-ink-gray-5">
					{{
						__(
							"Costs show up here as timesheets, purchase invoices and stock consumption are booked against this project."
						)
					}}
				</p>
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
				<Alert v-if="alert" v-bind="alert" />
				<div
					class="grid grid-cols-2 gap-5"
					:class="kpis.length === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-4'"
				>
					<NumberCard v-for="kpi in kpis" :key="kpi.label" :title="kpi.label" :value="kpi.value">
						<template v-if="kpi.hint" #title-suffix>
							<Tooltip :text="kpi.hint">
								<span
									class="lucide-info size-[1em] text-ink-gray-4"
									role="img"
									:aria-label="kpi.hint"
								/>
							</Tooltip>
						</template>
						<template v-if="kpi.sub" #caption>
							<span class="text-ink-gray-5">{{ kpi.sub }}</span>
						</template>
					</NumberCard>
				</div>
				<div class="grid gap-5 lg:grid-cols-5">
					<BudgetCard class="lg:col-span-2" :view="view" />
					<CostTrend class="lg:col-span-3" :view="view" />
				</div>
				<div class="grid gap-5 lg:grid-cols-2">
					<CostBreakdown :view="view" />
					<CostDrivers v-if="view.drivers" :view="view" />
				</div>
				<div v-if="!view.internal" class="grid gap-5 lg:grid-cols-2">
					<BillingCard v-if="view.billing" :view="view" />
					<MarginCard :view="view" />
				</div>
				<RateGapsDialog v-if="view.rate_gaps" v-model:open="show_rate_gaps" :view="view" />
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
