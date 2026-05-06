<template>
  <div class="flex flex-col gap-6 p-6">

    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">Tenant Management</h1>
        <p class="text-sm text-muted-foreground mt-1">Create and manage tenant accounts and plan assignments</p>
      </div>
      <div class="flex gap-2">
        <Button variant="outline" size="sm" @click="openPlanManager">
          <Monitor class="h-4 w-4" />
          Manage Plans
        </Button>
        <Button size="sm" @click="showCreate = true">
          <Plus class="h-4 w-4" />
          New Tenant
        </Button>
      </div>
    </div>

    <!-- Tenants Table -->
    <Card class="overflow-hidden">
      <div v-if="loading" class="flex justify-center p-12">
        <Loader2 class="h-7 w-7 animate-spin text-primary" />
      </div>
      <div v-else-if="!tenants.length" class="flex flex-col items-center gap-3 py-16 text-muted-foreground">
        <Users class="h-10 w-10" />
        <p class="text-sm">No tenants yet</p>
      </div>
      <div v-else class="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Username</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Plan &amp; Usage</TableHead>
              <TableHead>Assigned Clients</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="t in tenants" :key="t.id" class="hover:bg-muted/30">
              <TableCell>
                <div class="flex items-center gap-2.5">
                  <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground text-xs font-bold">
                    {{ t.username.slice(0,2).toUpperCase() }}
                  </div>
                  <div>
                    <p class="text-sm font-semibold text-foreground">{{ t.username }}</p>
                    <p class="text-[11px] text-muted-foreground">{{ t.email }}</p>
                  </div>
                </div>
              </TableCell>
              <TableCell class="text-sm text-foreground">{{ t.company_name || '—' }}</TableCell>
              <TableCell>
                <div class="flex flex-col gap-1.5 min-w-[160px]">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <Badge :variant="t.plan ? 'secondary' : 'outline'">{{ t.plan || 'No Plan' }}</Badge>
                    <Badge v-if="t.stripe_subscription_status" :variant="stripeVariant(t.stripe_subscription_status)" class="text-[9px]">{{ t.stripe_subscription_status }}</Badge>
                    <span v-if="t.trial_ends_at && new Date(t.trial_ends_at) > new Date()" class="rounded-full bg-violet-100 text-violet-700 text-[9px] font-bold px-1.5 py-0.5">Trial</span>
                  </div>
                  <template v-if="t.plan && t.plan_max_messages">
                    <div class="h-1 w-full rounded-full bg-muted overflow-hidden">
                      <div class="h-full rounded-full transition-all" :class="usageBarClass(t.messages_this_month, t.plan_max_messages)" :style="{ width: usagePct(t.messages_this_month, t.plan_max_messages) + '%' }"></div>
                    </div>
                    <span class="text-[10px] text-muted-foreground">{{ t.messages_this_month }} / {{ t.plan_max_messages < 0 ? '∞' : t.plan_max_messages }} msgs</span>
                  </template>
                </div>
              </TableCell>
              <TableCell>
                <div class="flex flex-wrap gap-1.5">
                  <span v-if="!t.client_details || !t.client_details.length" class="text-xs text-muted-foreground italic">None assigned</span>
                  <span
                    v-for="c in t.client_details" :key="c.id"
                    class="rounded-full border px-2 py-0.5 text-[11px] font-semibold"
                    :style="{ background: (c.chatbot_color || '#6366F1') + '18', color: c.chatbot_color || '#6366F1', borderColor: (c.chatbot_color || '#6366F1') + '44' }"
                    :title="c.domain_url"
                  >{{ c.name }}</span>
                </div>
              </TableCell>
              <TableCell>
                <div class="flex flex-wrap gap-1">
                  <Button variant="outline" size="sm" class="text-blue-600 border-blue-200 hover:bg-blue-50 h-7 px-2 text-xs" @click="openEdit(t)">Edit</Button>
                  <Button variant="outline" size="sm" class="text-primary border-primary/30 hover:bg-primary/10 h-7 px-2 text-xs" @click="openPlan(t)">Plan</Button>
                  <Button variant="ghost" size="icon" class="h-7 w-7" title="Plan history" @click="openHistory(t)">
                    <Clock class="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" class="h-7 w-7" title="Subscription" @click="openSubscription(t)">💳</Button>
                  <Button variant="ghost" size="icon" class="h-7 w-7" title="Feature overrides" @click="openOverrides(t)">🎁</Button>
                  <Button variant="outline" size="sm" class="text-emerald-600 border-emerald-200 hover:bg-emerald-50 h-7 px-2 text-xs" @click="loginAsTenant(t)" :disabled="impersonating === t.id">
                    {{ impersonating === t.id ? '…' : 'Login As' }}
                  </Button>
                  <Button variant="outline" size="sm" class="text-destructive border-destructive/30 hover:bg-destructive/10 h-7 px-2 text-xs" @click="confirmDelete(t)">Delete</Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </Card>

    <!-- Toast -->
    <div v-if="impersonateToast" class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 rounded-lg px-5 py-3 text-sm font-semibold shadow-lg" :class="impersonateToast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-destructive text-destructive-foreground'">
      {{ impersonateToast.msg }}
    </div>

    <!-- Create Tenant Dialog -->
    <Dialog :open="showCreate" @close="showCreate = false">
      <DialogHeader><DialogTitle>New Tenant</DialogTitle></DialogHeader>
      <div class="px-6 pb-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <Label>Username *</Label>
            <Input v-model="createForm.username" placeholder="tenant_username" />
          </div>
          <div class="space-y-1.5">
            <Label>Password *</Label>
            <Input v-model="createForm.password" type="password" placeholder="••••••••" />
          </div>
          <div class="space-y-1.5">
            <Label>Email</Label>
            <Input v-model="createForm.email" type="email" placeholder="tenant@company.com" />
          </div>
          <div class="space-y-1.5">
            <Label>Company Name</Label>
            <Input v-model="createForm.company_name" placeholder="Acme Corp" />
          </div>
          <div class="col-span-2 space-y-1.5">
            <Label>Plan</Label>
            <select v-model="createForm.plan_id" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
              <option value="">No plan</option>
              <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }} (${{ p.price_monthly }}/mo)</option>
            </select>
          </div>
          <div class="col-span-2 space-y-1.5">
            <Label>Assign Clients</Label>
            <div class="max-h-48 overflow-y-auto space-y-2 rounded-md border border-border p-2">
              <p v-if="!allClients.length" class="text-xs text-muted-foreground p-2">No clients available — create a client first.</p>
              <label v-for="c in allClients" :key="c.id" class="flex items-center gap-3 cursor-pointer rounded-lg border p-2.5 transition-colors" :class="createForm.client_ids.includes(c.id) ? 'border-primary bg-primary/5' : 'border-transparent hover:border-border'">
                <input type="checkbox" :value="c.id" v-model="createForm.client_ids" class="hidden" />
                <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white text-[10px] font-bold" :style="{ background: c.chatbot_color || '#6366F1' }">{{ c.name.slice(0,2).toUpperCase() }}</div>
                <div class="flex-1">
                  <p class="text-sm font-medium text-foreground">{{ c.name }}</p>
                  <p class="text-[11px] text-muted-foreground">{{ (c.domain_url || '').replace(/https?:\/\//, '') }}</p>
                </div>
                <span v-if="c.tenant_name" class="text-[10px] font-bold text-amber-500">Already: {{ c.tenant_name }}</span>
              </label>
            </div>
          </div>
        </div>
        <p v-if="createError" class="mt-3 text-xs text-destructive">{{ createError }}</p>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="showCreate = false">Cancel</Button>
        <Button @click="createTenant" :disabled="creating">
          <Loader2 v-if="creating" class="h-4 w-4 animate-spin" />
          Create Tenant
        </Button>
      </DialogFooter>
    </Dialog>

    <!-- Edit Tenant Dialog -->
    <Dialog :open="!!editTenant" @close="editTenant = null">
      <DialogHeader><DialogTitle>Edit: {{ editTenant?.username }}</DialogTitle></DialogHeader>
      <div class="px-6 pb-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <Label>Email</Label>
            <Input v-model="editForm.email" type="email" />
          </div>
          <div class="space-y-1.5">
            <Label>Company Name</Label>
            <Input v-model="editForm.company_name" />
          </div>
          <div class="col-span-2 space-y-1.5">
            <Label>New Password (leave blank to keep current)</Label>
            <Input v-model="editForm.password" type="password" placeholder="••••••••" />
          </div>
          <div class="col-span-2 space-y-1.5">
            <Label>Assigned Clients</Label>
            <div class="max-h-48 overflow-y-auto space-y-2 rounded-md border border-border p-2">
              <p v-if="!allClients.length" class="text-xs text-muted-foreground p-2">No clients available.</p>
              <label v-for="c in allClients" :key="c.id" class="flex items-center gap-3 cursor-pointer rounded-lg border p-2.5 transition-colors" :class="editForm.client_ids.includes(c.id) ? 'border-primary bg-primary/5' : 'border-transparent hover:border-border'">
                <input type="checkbox" :value="c.id" v-model="editForm.client_ids" class="hidden" />
                <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white text-[10px] font-bold" :style="{ background: c.chatbot_color || '#6366F1' }">{{ c.name.slice(0,2).toUpperCase() }}</div>
                <div class="flex-1">
                  <p class="text-sm font-medium text-foreground">{{ c.name }}</p>
                  <p class="text-[11px] text-muted-foreground">{{ (c.domain_url || '').replace(/https?:\/\//, '') }}</p>
                </div>
                <span v-if="c.tenant_name && !editForm.client_ids.includes(c.id)" class="text-[10px] font-bold text-amber-500">Owned by: {{ c.tenant_name }}</span>
              </label>
            </div>
          </div>
        </div>
        <p v-if="editError" class="mt-3 text-xs text-destructive">{{ editError }}</p>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="editTenant = null">Cancel</Button>
        <Button @click="saveTenant" :disabled="saving">
          <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
          Save Changes
        </Button>
      </DialogFooter>
    </Dialog>

    <!-- Plan Management Dialog -->
    <Dialog :open="!!planTenant" @close="planTenant = null" class="max-w-2xl">
      <DialogHeader><DialogTitle>Plan Management — {{ planTenant?.username }}</DialogTitle></DialogHeader>
      <div class="px-6 pb-4 space-y-5 max-h-[70vh] overflow-y-auto">

        <!-- Current usage -->
        <div v-if="planTenant?.plan" class="rounded-lg bg-muted p-4 space-y-3">
          <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Current Usage — {{ planTenant.plan }}</p>
          <div class="space-y-2.5">
            <div>
              <div class="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Sessions this month</span>
                <span class="font-semibold text-foreground">{{ planTenant.sessions_this_month }} / {{ planTenant.plan_max_sessions || '∞' }}</span>
              </div>
              <div class="h-1.5 w-full rounded-full bg-background overflow-hidden">
                <div class="h-full rounded-full" :class="usageBarClass(planTenant.sessions_this_month, planTenant.plan_max_sessions)" :style="{ width: usagePct(planTenant.sessions_this_month, planTenant.plan_max_sessions)+'%' }"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Clients assigned</span>
                <span class="font-semibold text-foreground">{{ planTenant.clients_count }} / {{ planTenant.plan_max_clients || '∞' }}</span>
              </div>
              <div class="h-1.5 w-full rounded-full bg-background overflow-hidden">
                <div class="h-full rounded-full" :class="usageBarClass(planTenant.clients_count, planTenant.plan_max_clients)" :style="{ width: usagePct(planTenant.clients_count, planTenant.plan_max_clients)+'%' }"></div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">No plan assigned yet.</div>

        <!-- Plan options -->
        <div>
          <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Select New Plan</p>
          <div class="space-y-2">
            <div
              v-for="p in plans" :key="p.id"
              class="rounded-lg border-2 p-3.5 cursor-pointer transition-all relative"
              :class="selectedPlanId === p.id ? 'border-primary bg-primary/5' : p.name === planTenant?.plan ? 'border-emerald-300 bg-emerald-50/50' : 'border-border hover:border-border/70'"
              @click="selectedPlanId = p.id"
            >
              <div class="flex items-start justify-between">
                <div>
                  <p class="text-sm font-bold text-foreground">{{ p.name }}</p>
                  <p class="text-[11px] text-muted-foreground mt-0.5">
                    {{ p.max_clients }} clients · {{ p.max_messages_per_month < 0 ? '∞' : p.max_messages_per_month.toLocaleString() }} msgs/mo · {{ p.max_sessions_per_month < 0 ? '∞' : p.max_sessions_per_month.toLocaleString() }} sessions/mo
                  </p>
                </div>
                <p class="text-lg font-bold text-primary">${{ p.price_monthly }}<span class="text-[11px] font-normal text-muted-foreground">/mo</span></p>
              </div>
              <div class="flex flex-wrap gap-1 mt-2.5">
                <span v-for="f in planFlags(p)" :key="f.key" class="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-semibold" :class="f.on ? 'bg-emerald-100 text-emerald-700' : 'bg-muted text-muted-foreground/50'">
                  {{ f.on ? '✓' : '✕' }} {{ f.label }}
                </span>
              </div>
              <span v-if="p.name === planTenant?.plan" class="absolute top-2 right-2 rounded text-[9px] font-bold bg-emerald-500 text-white px-1.5 py-0.5 uppercase">Current</span>
            </div>
          </div>
        </div>

        <!-- Remarks -->
        <div class="space-y-1.5">
          <Label class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Remarks (optional)</Label>
          <Textarea v-model="planRemarks" placeholder="e.g. Upgraded as per client request on call…" :rows="2" />
        </div>

        <!-- Plan History -->
        <div v-if="planHistoryLoading" class="text-xs text-muted-foreground text-center py-3">Loading history…</div>
        <template v-else-if="planHistoryData.length">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Plan History</p>
            <div class="border-l-2 border-border ml-1.5 pl-4 space-y-4">
              <div v-for="h in planHistoryData" :key="h.id" class="relative">
                <div class="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-primary border-2 border-background"></div>
                <div class="flex items-center gap-2 text-sm">
                  <span class="text-muted-foreground font-medium">{{ h.from_plan || 'None' }}</span>
                  <span class="text-muted-foreground">→</span>
                  <span class="font-bold text-primary">{{ h.to_plan || 'None' }}</span>
                </div>
                <p class="text-[11px] text-muted-foreground mt-0.5">by <strong>{{ h.changed_by }}</strong> · {{ fmtDate(h.changed_at) }}</p>
                <p v-if="h.remarks" class="text-[11px] italic text-muted-foreground mt-0.5">"{{ h.remarks }}"</p>
              </div>
            </div>
          </div>
        </template>
        <p v-else-if="!planHistoryLoading" class="text-xs italic text-muted-foreground text-center">No plan changes recorded yet.</p>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="planTenant = null">Close</Button>
        <Button @click="savePlan" :disabled="!selectedPlanId || selectedPlanId === planTenant?.plan_id || savingPlan">
          <Loader2 v-if="savingPlan" class="h-4 w-4 animate-spin" />
          Assign Plan
        </Button>
      </DialogFooter>
    </Dialog>

    <!-- Plan History Only Dialog -->
    <Dialog :open="!!historyTenant && !planTenant" @close="historyTenant = null">
      <DialogHeader><DialogTitle>Plan History — {{ historyTenant?.username }}</DialogTitle></DialogHeader>
      <div class="px-6 pb-4">
        <div v-if="planHistoryLoading" class="text-sm text-muted-foreground text-center py-4">Loading…</div>
        <div v-else-if="!planHistoryData.length" class="text-xs italic text-muted-foreground text-center py-4">No plan changes recorded yet.</div>
        <div v-else class="border-l-2 border-border ml-1.5 pl-4 space-y-4">
          <div v-for="h in planHistoryData" :key="h.id" class="relative">
            <div class="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-primary border-2 border-background"></div>
            <div class="flex items-center gap-2 text-sm">
              <span class="text-muted-foreground">{{ h.from_plan || 'None' }}</span>
              <span class="text-muted-foreground">→</span>
              <span class="font-bold text-primary">{{ h.to_plan || 'None' }}</span>
            </div>
            <p class="text-[11px] text-muted-foreground mt-0.5">by <strong>{{ h.changed_by }}</strong> · {{ fmtDate(h.changed_at) }}</p>
            <p v-if="h.remarks" class="text-[11px] italic text-muted-foreground">"{{ h.remarks }}"</p>
          </div>
        </div>
      </div>
      <DialogFooter>
        <Button @click="historyTenant = null">Close</Button>
      </DialogFooter>
    </Dialog>

    <!-- Plan Manager Dialog -->
    <Dialog :open="showPlanManager" @close="showPlanManager = false">
      <DialogHeader><DialogTitle>Plan Manager</DialogTitle></DialogHeader>
      <div class="px-6 pb-4 space-y-4">
        <p class="text-xs text-muted-foreground">Set the Stripe Price ID for each plan to enable self-service billing. Find Price IDs in your Stripe dashboard → Products.</p>
        <div class="space-y-3">
          <div v-for="p in plans" :key="p.id" class="flex items-center gap-4 rounded-lg border p-3">
            <div class="flex-1">
              <p class="text-sm font-semibold text-foreground">{{ p.name }}</p>
              <p class="text-xs text-muted-foreground">${{ p.price_monthly }}/mo · {{ p.max_sessions_per_month }} sessions</p>
            </div>
            <Input
              class="flex-1 text-xs"
              :value="planPriceIds[p.id] ?? p.stripe_price_id ?? ''"
              @input="planPriceIds[p.id] = $event.target.value"
              placeholder="price_xxx"
            />
          </div>
        </div>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="showPlanManager = false">Cancel</Button>
        <Button @click="savePlanPriceIds" :disabled="savingPriceIds">
          <Loader2 v-if="savingPriceIds" class="h-4 w-4 animate-spin" />
          Save Price IDs
        </Button>
      </DialogFooter>
    </Dialog>

    <!-- Feature Overrides Dialog -->
    <Dialog :open="!!overrideTenant" @close="overrideTenant = null">
      <DialogHeader><DialogTitle>Feature Overrides — {{ overrideTenant?.username }}</DialogTitle></DialogHeader>
      <div class="px-6 pb-4 space-y-4">
        <p class="text-xs text-muted-foreground">Grant or revoke specific features for this tenant, overriding their plan.</p>
        <div v-if="overridesLoading" class="text-sm text-muted-foreground text-center py-3">Loading…</div>
        <div v-else-if="!tenantOverrides.length" class="text-xs italic text-muted-foreground">No active overrides. Their plan features apply.</div>
        <div v-else class="space-y-2">
          <div v-for="ov in tenantOverrides" :key="ov.id" class="flex items-center gap-3 rounded-lg border p-2.5">
            <span class="font-mono text-xs font-medium text-primary flex-1">{{ ov.feature_name }}</span>
            <Badge :variant="ov.enabled ? 'success' : 'destructive'" class="text-[10px]">{{ ov.enabled ? 'GRANTED' : 'REVOKED' }}</Badge>
            <span v-if="ov.expires_at" class="text-[10px] text-muted-foreground">exp {{ fmtDate(ov.expires_at) }}</span>
            <span v-if="ov.reason" class="text-[10px] italic text-muted-foreground">"{{ ov.reason }}"</span>
            <Button variant="ghost" size="icon" class="h-6 w-6 text-destructive hover:bg-destructive/10" @click="deleteOverride(ov.id)" :disabled="deletingOverride === ov.id">✕</Button>
          </div>
        </div>
        <Separator />
        <div class="space-y-3">
          <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Add Override</p>
          <div class="grid grid-cols-2 gap-3">
            <select v-model="newOverride.feature_name" class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
              <option value="">Select feature…</option>
              <option v-for="f in allFeatures" :key="f.key" :value="f.key">{{ f.label }}</option>
            </select>
            <select v-model="newOverride.enabled" class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
              <option :value="true">Grant (enable)</option>
              <option :value="false">Revoke (disable)</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <input type="datetime-local" v-model="newOverride.expires_at" class="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring" />
            <Input v-model="newOverride.reason" placeholder="e.g. 30-day trial" />
          </div>
          <p v-if="overrideError" class="text-xs text-destructive">{{ overrideError }}</p>
        </div>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="overrideTenant = null">Close</Button>
        <Button @click="addOverride" :disabled="addingOverride || !newOverride.feature_name">
          <Loader2 v-if="addingOverride" class="h-4 w-4 animate-spin" />
          Add Override
        </Button>
      </DialogFooter>
    </Dialog>

    <!-- Subscription Dialog -->
    <Dialog :open="!!subTenant" @close="subTenant = null" class="max-w-2xl">
      <DialogHeader><DialogTitle>Subscription — {{ subTenant?.username }}</DialogTitle></DialogHeader>
      <div class="px-6 pb-4 max-h-[70vh] overflow-y-auto">
        <div v-if="subLoading" class="text-sm text-muted-foreground text-center py-6">Loading subscription data…</div>
        <div v-else-if="subData" class="space-y-5">
          <!-- Status -->
          <div class="flex items-center gap-3 flex-wrap">
            <p class="text-base font-bold text-foreground">{{ subData.plan?.name || 'No Plan' }}</p>
            <Badge :variant="stripeVariant(subData.stripe_subscription_status)">{{ subData.stripe_subscription_status || 'No subscription' }}</Badge>
            <Badge v-if="subData.billing_interval" variant="outline" class="text-[10px] uppercase">{{ subData.billing_interval }}</Badge>
          </div>

          <!-- Usage bars -->
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Usage This Month</p>
            <div class="grid grid-cols-2 gap-3">
              <div v-for="res in subUsageRows" :key="res.key" class="rounded-lg border p-3 space-y-2">
                <div class="flex justify-between text-xs">
                  <span class="text-muted-foreground font-medium">{{ res.label }}</span>
                  <span class="font-bold text-foreground">{{ res.used }} / {{ res.limit < 0 ? '∞' : res.limit }}</span>
                </div>
                <div class="h-1.5 rounded-full bg-muted overflow-hidden">
                  <div class="h-full rounded-full" :class="usageBarClass(res.used, res.limit < 0 ? 0 : res.limit)" :style="{ width: usagePct(res.used, res.limit < 0 ? 0 : res.limit)+'%' }"></div>
                </div>
                <button class="text-[10px] font-semibold rounded bg-destructive/10 border border-destructive/20 text-destructive px-2 py-0.5 hover:bg-destructive/20 cursor-pointer" @click="resetUsage(res.resetKey)" :disabled="resetting">Reset</button>
              </div>
            </div>
          </div>

          <!-- Add-on top-ups -->
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Add-On Top-Ups</p>
            <div class="grid grid-cols-3 gap-3">
              <div v-for="a in addonRows" :key="a.key" class="space-y-1.5">
                <Label class="text-xs">{{ a.label }}</Label>
                <Input type="number" min="0" v-model.number="subForm[a.key]" />
              </div>
            </div>
          </div>

          <!-- Trial & billing interval -->
          <div>
            <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Trial &amp; Billing</p>
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-1.5">
                <Label class="text-xs">Trial ends at</Label>
                <input type="datetime-local" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring" v-model="subForm.trial_ends_at" />
              </div>
              <div class="space-y-1.5">
                <Label class="text-xs">Billing interval</Label>
                <select class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring" v-model="subForm.billing_interval">
                  <option value="monthly">Monthly</option>
                  <option value="annual">Annual</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Stripe info -->
          <div class="rounded-lg bg-muted p-3 space-y-1.5 text-xs">
            <div class="flex gap-3"><span class="text-muted-foreground w-32">Customer ID</span><span class="font-mono text-foreground">{{ subData.stripe_customer_id || '—' }}</span></div>
            <div class="flex gap-3"><span class="text-muted-foreground w-32">Subscription ID</span><span class="font-mono text-foreground">{{ subData.stripe_subscription_id || '—' }}</span></div>
          </div>

          <p v-if="subError" class="text-xs text-destructive">{{ subError }}</p>
        </div>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="subTenant = null">Close</Button>
        <Button @click="saveSubscription" :disabled="savingSub">
          <Loader2 v-if="savingSub" class="h-4 w-4 animate-spin" />
          Save Changes
        </Button>
      </DialogFooter>
    </Dialog>

    <!-- Delete Confirm Dialog -->
    <Dialog :open="!!deleteTenant" @close="deleteTenant = null">
      <div class="p-6 text-center space-y-3">
        <div class="text-3xl">⚠️</div>
        <h3 class="text-base font-bold text-foreground">Delete Tenant</h3>
        <p class="text-sm text-muted-foreground">This will permanently delete <strong>{{ deleteTenant?.username }}</strong> and all their data.</p>
      </div>
      <DialogFooter>
        <Button variant="ghost" @click="deleteTenant = null">Cancel</Button>
        <Button variant="destructive" @click="doDelete" :disabled="deleting">
          <Loader2 v-if="deleting" class="h-4 w-4 animate-spin" />
          Delete
        </Button>
      </DialogFooter>
    </Dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Plus, Loader2, Users, Clock, Monitor } from 'lucide-vue-next'
import { useAdminApi } from '../composables/useAdminApi'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Textarea from '@/components/ui/Textarea.vue'
import Separator from '@/components/ui/Separator.vue'
import Badge from '@/components/ui/Badge.vue'
import Table from '@/components/ui/Table.vue'
import TableHeader from '@/components/ui/TableHeader.vue'
import TableBody from '@/components/ui/TableBody.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableHead from '@/components/ui/TableHead.vue'
import TableCell from '@/components/ui/TableCell.vue'
import Dialog from '@/components/ui/Dialog.vue'
import DialogHeader from '@/components/ui/DialogHeader.vue'
import DialogTitle from '@/components/ui/DialogTitle.vue'
import DialogFooter from '@/components/ui/DialogFooter.vue'

const api = useAdminApi()
const tenants = ref([])
const plans = ref([])
const allClients = ref([])
const loading = ref(false)

const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = ref({ username: '', password: '', email: '', company_name: '', plan_id: '', client_ids: [] })

const editTenant = ref(null)
const editForm = ref({})
const saving = ref(false)
const editError = ref('')

const planTenant = ref(null)
const selectedPlanId = ref(null)
const savingPlan = ref(false)
const planRemarks = ref('')
const planHistoryData = ref([])
const planHistoryLoading = ref(false)

const historyTenant = ref(null)
const deleteTenant = ref(null)
const deleting = ref(false)

const impersonating = ref(null)
const impersonateToast = ref(null)

const showPlanManager = ref(false)
const planPriceIds = ref({})
const savingPriceIds = ref(false)

const overrideTenant = ref(null)
const tenantOverrides = ref([])
const overridesLoading = ref(false)
const addingOverride = ref(false)
const deletingOverride = ref(null)
const overrideError = ref('')
const newOverride = ref({ feature_name: '', enabled: true, expires_at: '', reason: '' })

const subTenant = ref(null)
const subData = ref(null)
const subLoading = ref(false)
const savingSub = ref(false)
const resetting = ref(false)
const subError = ref('')
const subForm = ref({ trial_ends_at: '', billing_interval: 'monthly', addon_messages: 0, addon_images: 0, addon_voice: 0 })

const subUsageRows = computed(() => {
  if (!subData.value) return []
  const d = subData.value
  const plan = d.plan || {}
  return [
    { key: 'messages', label: 'AI Messages', used: d.messages_this_month, limit: plan.max_messages_per_month ?? -1, resetKey: 'reset_messages' },
    { key: 'sessions', label: 'Sessions',    used: d.sessions_this_month, limit: plan.max_sessions_per_month  ?? -1, resetKey: 'reset_sessions' },
    { key: 'images',   label: 'Images',      used: d.images_this_month,   limit: plan.max_images_per_month   ?? -1, resetKey: 'reset_images' },
    { key: 'voice',    label: 'Voice',       used: d.voice_this_month,    limit: plan.max_voice_per_month    ?? -1, resetKey: 'reset_voice' },
  ]
})

const addonRows = [
  { key: 'addon_messages', label: 'Bonus messages' },
  { key: 'addon_images',   label: 'Bonus images' },
  { key: 'addon_voice',    label: 'Bonus voice cmds' },
]

function stripeVariant(status) {
  if (!status || status === 'none') return 'secondary'
  if (status === 'active' || status === 'trialing') return 'success'
  if (status === 'past_due') return 'warning'
  return 'destructive'
}

function usagePct(used, max) {
  if (!max || max < 0) return 0
  return Math.min(Math.round((used / max) * 100), 100)
}
function usageBarClass(used, max) {
  if (!max || max < 0) return 'bg-emerald-500'
  const pct = (used / max) * 100
  if (pct >= 85) return 'bg-red-500'
  if (pct >= 60) return 'bg-amber-500'
  return 'bg-emerald-500'
}

function fmtDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) +
    ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}

const FLAG_LABELS = [
  { key: 'allow_whatsapp', label: 'WhatsApp' }, { key: 'allow_telegram', label: 'Telegram' },
  { key: 'allow_byok', label: 'BYOK' }, { key: 'allow_hubspot', label: 'HubSpot' },
  { key: 'allow_slack', label: 'Slack' }, { key: 'allow_webhooks', label: 'Webhooks' },
  { key: 'allow_god_view', label: 'God View' }, { key: 'allow_csv_export', label: 'CSV Export' },
  { key: 'allow_voice_input', label: 'Voice' }, { key: 'allow_image_input', label: 'Images' },
  { key: 'allow_advanced_reports', label: 'Adv. Reports' }, { key: 'remove_branding', label: 'No Branding' },
  { key: 'allow_custom_domain', label: 'Domain' }, { key: 'allow_api_access', label: 'API' },
  { key: 'priority_support', label: 'Priority Sup.' },
]

function planFlags(plan) {
  return FLAG_LABELS.map(f => ({ key: f.key, label: f.label, on: !!plan[f.key] }))
}

const allFeatures = [
  { key: 'allow_whatsapp', label: 'WhatsApp Business' }, { key: 'allow_telegram', label: 'Telegram Bot' },
  { key: 'allow_messenger', label: 'Facebook Messenger' }, { key: 'allow_byok', label: 'Custom AI (BYOK)' },
  { key: 'allow_hubspot', label: 'HubSpot CRM' }, { key: 'allow_slack', label: 'Slack Notifications' },
  { key: 'allow_webhooks', label: 'Outbound Webhooks' }, { key: 'allow_god_view', label: 'Live Takeover (God View)' },
  { key: 'allow_canned_responses', label: 'Canned Responses' }, { key: 'allow_conversation_tags', label: 'Conversation Tags' },
  { key: 'allow_csv_export', label: 'Analytics CSV Export' }, { key: 'allow_voice_input', label: 'Voice Input' },
  { key: 'allow_image_input', label: 'Image Input' }, { key: 'allow_fomo_triggers', label: 'FOMO Triggers' },
  { key: 'allow_advanced_reports', label: 'Advanced Analytics' }, { key: 'remove_branding', label: 'Remove Branding' },
  { key: 'allow_custom_domain', label: 'Custom Domain' }, { key: 'allow_api_access', label: 'API Access' },
  { key: 'allow_multi_language', label: 'Multi-Language' }, { key: 'priority_support', label: 'Priority Support' },
]

async function load() {
  loading.value = true
  try {
    const [t, p, c] = await Promise.all([api.getTenants(), api.getPlans(), api.getClients()])
    tenants.value = t || []
    plans.value = p || []
    allClients.value = c || []
  } catch (e) { console.error(e) } finally { loading.value = false }
}

async function loadPlanHistory(tenantId) {
  planHistoryLoading.value = true
  planHistoryData.value = []
  try { planHistoryData.value = await api.getPlanHistory(tenantId) || [] }
  catch (e) { console.error(e) } finally { planHistoryLoading.value = false }
}

async function createTenant() {
  createError.value = ''
  if (!createForm.value.username || !createForm.value.password) { createError.value = 'Username and password are required.'; return }
  creating.value = true
  try {
    const t = await api.createTenant({ ...createForm.value })
    tenants.value.unshift({ ...t, client_details: allClients.value.filter(c => (t.clients || []).includes(c.id)) })
    allClients.value = await api.getClients() || []
    showCreate.value = false
    createForm.value = { username: '', password: '', email: '', company_name: '', plan_id: '', client_ids: [] }
  } catch (e) { createError.value = e.message } finally { creating.value = false }
}

function openEdit(t) {
  editTenant.value = t
  editForm.value = { email: t.email, company_name: t.company_name, password: '', client_ids: [...(t.clients || [])] }
  editError.value = ''
}

async function saveTenant() {
  editError.value = ''
  saving.value = true
  try {
    await api.updateTenant(editTenant.value.id, editForm.value)
    const [freshTenants, freshClients] = await Promise.all([api.getTenants(), api.getClients()])
    tenants.value = freshTenants || tenants.value
    allClients.value = freshClients || allClients.value
    editTenant.value = null
  } catch (e) { editError.value = e.message } finally { saving.value = false }
}

function openPlan(t) {
  planTenant.value = t
  selectedPlanId.value = t.plan_id || null
  planRemarks.value = ''
  loadPlanHistory(t.id)
}

async function openHistory(t) {
  historyTenant.value = t
  loadPlanHistory(t.id)
}

async function savePlan() {
  if (!selectedPlanId.value) return
  savingPlan.value = true
  try {
    const result = await api.assignPlan(planTenant.value.id, selectedPlanId.value, planRemarks.value)
    const idx = tenants.value.findIndex(x => x.id === planTenant.value.id)
    if (idx >= 0) {
      tenants.value[idx] = { ...tenants.value[idx], plan: result.plan, plan_id: result.plan_id, plan_max_sessions: result.plan_max_sessions, plan_max_clients: result.plan_max_clients }
      planTenant.value = { ...tenants.value[idx] }
    }
    planRemarks.value = ''
    await loadPlanHistory(planTenant.value.id)
  } catch (e) { alert(e.message) } finally { savingPlan.value = false }
}

async function loginAsTenant(t) {
  impersonating.value = t.id
  try {
    const data = await api.impersonateTenant(t.id)
    const prevToken = localStorage.getItem('cf_access_token')
    const prevUser = localStorage.getItem('cf_user')
    localStorage.setItem('cf_access_token', data.access)
    localStorage.setItem('cf_user', JSON.stringify({ ...data.tenant, role: data.tenant.role }))
    localStorage.setItem('cf_impersonate_return_token', prevToken)
    localStorage.setItem('cf_impersonate_return_user', prevUser)
    localStorage.setItem('cf_impersonating', 'true')
    showToast(`Logged in as ${data.tenant.username} (${data.tenant.company_name})`, 'success')
    setTimeout(() => { window.location.href = '/admin/' }, 1200)
  } catch (e) { showToast(e.message || 'Impersonation failed', 'error') } finally { impersonating.value = null }
}

function showToast(msg, type = 'success') {
  impersonateToast.value = { msg, type }
  setTimeout(() => { impersonateToast.value = null }, 3000)
}

function confirmDelete(t) { deleteTenant.value = t }

async function doDelete() {
  deleting.value = true
  try {
    await api.deleteTenant(deleteTenant.value.id)
    tenants.value = tenants.value.filter(x => x.id !== deleteTenant.value.id)
    deleteTenant.value = null
  } catch (e) { alert(e.message) } finally { deleting.value = false }
}

function openPlanManager() { planPriceIds.value = {}; showPlanManager.value = true }

async function savePlanPriceIds() {
  savingPriceIds.value = true
  try {
    await Promise.all(Object.entries(planPriceIds.value).map(([id, stripe_price_id]) => api.updatePlan(id, { stripe_price_id: stripe_price_id || null })))
    plans.value = await api.getPlans() || []
    showPlanManager.value = false
  } catch (e) { alert(e.message || 'Failed to save price IDs.') } finally { savingPriceIds.value = false }
}

async function openOverrides(t) {
  overrideTenant.value = t
  tenantOverrides.value = []
  overrideError.value = ''
  newOverride.value = { feature_name: '', enabled: true, expires_at: '', reason: '' }
  overridesLoading.value = true
  try { tenantOverrides.value = await api.getTenantFeatureOverrides(t.id) || [] }
  catch (e) { overrideError.value = e.message } finally { overridesLoading.value = false }
}

async function addOverride() {
  if (!newOverride.value.feature_name) return
  overrideError.value = ''
  addingOverride.value = true
  try {
    const created = await api.createFeatureOverride(overrideTenant.value.id, { feature_name: newOverride.value.feature_name, enabled: newOverride.value.enabled, reason: newOverride.value.reason || '', expires_at: newOverride.value.expires_at || null })
    tenantOverrides.value.unshift(created)
    newOverride.value = { feature_name: '', enabled: true, expires_at: '', reason: '' }
  } catch (e) { overrideError.value = e.message || 'Failed to add override.' } finally { addingOverride.value = false }
}

async function deleteOverride(overrideId) {
  deletingOverride.value = overrideId
  try {
    await api.deleteFeatureOverride(overrideTenant.value.id, overrideId)
    tenantOverrides.value = tenantOverrides.value.filter(o => o.id !== overrideId)
  } catch (e) { alert(e.message || 'Failed to delete override.') } finally { deletingOverride.value = null }
}

async function openSubscription(t) {
  subTenant.value = t
  subData.value = null
  subError.value = ''
  subLoading.value = true
  try {
    const d = await api.getTenantSubscription(t.id)
    subData.value = d
    subForm.value = { trial_ends_at: d.trial_ends_at ? d.trial_ends_at.slice(0, 16) : '', billing_interval: d.billing_interval || 'monthly', addon_messages: d.addon_messages || 0, addon_images: d.addon_images || 0, addon_voice: d.addon_voice || 0 }
  } catch (e) { subError.value = e.message || 'Failed to load subscription.' } finally { subLoading.value = false }
}

async function saveSubscription() {
  savingSub.value = true
  subError.value = ''
  try {
    const payload = { billing_interval: subForm.value.billing_interval, addon_messages: subForm.value.addon_messages, addon_images: subForm.value.addon_images, addon_voice: subForm.value.addon_voice, trial_ends_at: subForm.value.trial_ends_at ? new Date(subForm.value.trial_ends_at).toISOString() : null }
    await api.updateTenantSubscription(subTenant.value.id, payload)
    subTenant.value = null
  } catch (e) { subError.value = e.message || 'Failed to save.' } finally { savingSub.value = false }
}

async function resetUsage(resetKey) {
  resetting.value = true
  try {
    await api.updateTenantSubscription(subTenant.value.id, { [resetKey]: true })
    const map = { reset_messages: 'messages_this_month', reset_sessions: 'sessions_this_month', reset_images: 'images_this_month', reset_voice: 'voice_this_month' }
    if (subData.value) subData.value[map[resetKey]] = 0
  } catch (e) { subError.value = e.message || 'Reset failed.' } finally { resetting.value = false }
}

onMounted(load)
</script>
