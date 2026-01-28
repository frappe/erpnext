<script setup>
import { ref, reactive, onMounted, computed } from 'vue';

const work_context = reactive({
    role: "Slab Loader",
    assigned_line: "",
    assigned_station: "Quarantine",
    assigned_shift: ""
});

const fetchWorkContext = async () => {
    const currentUser = await frappe.call({
        method: "erpnext.setup.doctype.employee.api.get_current_user_context",
    });

    if (currentUser.message) {
        work_context.role = currentUser.message.designation;
        work_context.assigned_line = currentUser.message.production_line;
        work_context.assigned_shift = currentUser.message.shift;
    }
};
const slabs = ref([]);
const searchQuery = ref('');

const fetchSlabs = async () => {
    try {
        const r = await frappe.call({
            method: 'erpnext.manufacturing.doctype.slab.api.get_slabs_in',
            args: {
                line: work_context.assigned_line,
                current_stage: "Quarantine"
            }
        });
        if (r.message) {
            slabs.value = r.message;
        }
    } catch (e) {
        console.error("Failed to fetch slabs", e);
    }
};

const filteredSlabs = computed(() => {
    let result = slabs.value;
    if (searchQuery.value) {
        const q = searchQuery.value.toLowerCase();
        result = result.filter(s =>
            s.name.toLowerCase().includes(q) ||
            s.template.toLowerCase().includes(q)
        );
    }
    // Sort by modified date ASC (oldest first)
    return [...result].sort((a, b) => new Date(a.modified) - new Date(b.modified));
});

const getThickness = (template) => {
    if (!template) return '';
    const parts = template.split('-');
    return parts[parts.length - 1].trim();
};

const getColorClass = (template) => {
    if (!template) return 'purple';
    const t = template.toLowerCase();
    if (t.includes('midnight blue')) return 'midnight-blue';
    if (t.includes('carrara white')) return 'carrara-white';
    if (t.includes('concrete grey')) return 'concrete-grey';
    return 'purple';
};

const now = ref(new Date());

const getDuration = (date_str) => {
    if (!date_str) return '';
    const modified = new Date(date_str);
    const diffMs = now.value - modified;

    if (diffMs < 0) return '0 minutes';

    const minutes = Math.floor(diffMs / 60000);
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    let duration = [];
    if (hours > 0) {
        duration.push(`${hours} ${hours === 1 ? 'hour' : 'hours'}`);
    }
    if (remainingMinutes > 0 || hours === 0) {
        duration.push(`${remainingMinutes} ${remainingMinutes === 1 ? 'minute' : 'minutes'}`);
    }

    return duration.join(' ');
};

frappe.realtime.on('slab_move', () => {
    fetchSlabs();
});

const minQuarantineHours = ref(0);

const fetchSettings = async () => {
    try {
        const doc = await frappe.db.get_doc('Mahi Granites Settings');
        if (doc) {
            minQuarantineHours.value = doc.min_quarantine_hours || 0;
        }
    } catch (e) {
        console.error("Failed to fetch settings", e);
    }
};

onMounted(async () => {
    await fetchWorkContext();
    fetchSlabs();
    fetchSettings();
    setInterval(() => {
        now.value = new Date();
    }, 60000);
});

const unloadToTrimming = (slab) => {
    const modified = new Date(slab.modified);
    const diffMs = new Date() - modified;
    const elapsedHours = diffMs / (1000 * 60 * 60);

    const performMove = async () => {
        try {
            await frappe.call({
                method: 'erpnext.manufacturing.doctype.slab.api.move_slab_to',
                args: {
                    slab_number: slab.name,
                    next_stage: "Trimming",
                    checkout_and_move: true,
                    job_card_number: slab.current_job_card
                },
                freeze: true,
                callback: (r) => {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Slab {0} unloaded to Trimming', [slab.name]),
                            indicator: 'green'
                        });
                        fetchSlabs();
                    }
                }
            });
        } catch (e) {
            frappe.msgprint(__('Failed to unload slab to Trimming.'));
        }
    };

    if (elapsedHours < minQuarantineHours.value) {
        frappe.confirm(
            __('The prescribed time for quarantine ({0} hours) has not passed for slab {1}. Do you want to proceed with the unloading anyway?', [minQuarantineHours.value, slab.name]),
            () => performMove()
        );
    } else {
        frappe.confirm(__('Are you sure you want to unload slab {0} to Trimming?', [slab.name]), () => performMove());
    }
};

</script>

<template>
    <div class="slab-loading-station">
        <header class="station-header d-flex justify-content-between align-items-center mb-5">
            <div>
                <h2 class="section-title">{{ __('Quarantine Inventory') }}</h2>
                <p class="section-subtitle">{{ __('Select quarantined slabs to unload onto the trimming line.') }}</p>
            </div>
            <div class="search-box">
                <span class="fa fa-search search-icon mr-2"></span>
                <input type="text" v-model="searchQuery" :placeholder="__('Search slab number or color...')">
            </div>
        </header>

        <TransitionGroup name="slab-list" tag="div" class="cards-grid">
            <div v-for="slab in slabs" :key="slab.name" class="slab-card">
                <div class="card-header" :class="getColorClass(slab.template)"></div>
                <div class="card-body">
                    <div class="card-top-row d-flex justify-content-between align-items-center mb-2">
                        <span class="slab-badge">{{ slab.template }}</span>
                        <span class="qc-badge passed">
                            <span class="fa fa-check mr-1"></span>
                            QC: Passed
                        </span>
                    </div>
                    <div class="slab-color-name font-weight-bold mb-2">{{ slab.name }}</div>
                    <div class="slab-meta-row text-muted small mb-3">
                        <span class="fa fa-clock-o mr-1"></span>
                        {{ __('In quarantine for') }} <span class="strong">{{ getDuration(slab.modified) }}</span>
                    </div>
                    <div class="slab-stats d-flex mb-4" style="gap: 2rem;">
                        <div class="stat-item w-100">
                            <div class="stat-label d-inline-block mr-2 text-muted small text-uppercase">{{
                                __('Thickness') }}</div>
                            <div class="stat-value d-inline-block font-weight-bold">{{ getThickness(slab.template) }}mm
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-primary w-100 font-weight-bold" @click="unloadToTrimming(slab)">
                        {{ __('Unload to Trimming') }}
                        <span class="fa fa-arrow-right ml-2" style="opacity: 0.5;"></span>
                    </button>
                </div>
            </div>
        </TransitionGroup>

        <div v-if="!filteredSlabs.length" class="empty-state text-center p-5 border rounded">
            <div class="text-muted">{{ __('No slabs found in quarantine.') }}</div>
        </div>
    </div>
</template>

<style scoped>
.empty-state {
    background: var(--fg-color);
    border: 1px solid var(--border-color) !important;
}

/* Animations */
.slab-list-enter-active,
.slab-list-leave-active {
    transition: all 0.5s ease;
}

.slab-list-enter-from {
    opacity: 0;
    transform: translateX(50px);
}

.slab-list-leave-to {
    opacity: 0;
    transform: scale(0.9);
}

.slab-list-move {
    transition: transform 0.5s ease;
}

.slab-loading-station {
    padding: 2rem;
    background: var(--bg-light-gray);
    min-height: 100vh;
}

.section-title {
    font-size: 1.75rem;
    font-weight: 600;
    margin: 0;
}

.section-subtitle {
    color: var(--text-muted);
    margin: 0.25rem 0 0;
}

.search-box {
    display: flex;
    align-items: center;
    padding: 0.625rem 1rem;
    background: var(--card-bg, #fff);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    min-width: 280px;
}

.search-box input {
    border: none;
    outline: none;
    background: transparent;
    width: 100%;
}

.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
}

.slab-card {
    background: var(--card-bg, #fff);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    overflow: hidden;
    transition: all 0.2s;
    box-shadow: var(--shadow-sm);
}

.slab-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
    height: 8px;
}

.card-header.midnight-blue {
    background: #1e3a5f;
}

.card-header.carrara-white {
    background: linear-gradient(90deg, #e8e8e8, #d0d0d0);
}

.card-header.concrete-grey {
    background: #808080;
}

.card-header.purple {
    background: #808080;
}

.card-body {
    padding: 1.25rem;
}

.slab-badge {
    padding: 0.25rem 0.75rem;
    background: var(--bg-light-gray, #f1f5f9);
    border-radius: 0.375rem;
    font-size: 0.8125rem;
    font-weight: 600;
}

.qc-badge {
    padding: 0.25rem 0.625rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.qc-badge.passed {
    background: #dcfce7;
    color: #16a34a;
}

.slab-color-name {
    font-size: 1.25rem;
}

.btn-primary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--text-color);
    border: 1px solid var(--text-color);
    color: var(--card-bg, #fff);
    padding: 0.75rem;
    font-size: 1rem;
}

.btn-primary:hover {
    background: var(--text-color);
    filter: brightness(0.8);
}
</style>
