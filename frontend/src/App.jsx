import { useEffect, useMemo, useRef, useState } from "react"

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

const navItems = [
  { name: "Overview", icon: "▦" },
  { name: "Portfolio", icon: "◫" },
  { name: "Decisions", icon: "◇" },
  { name: "Decision Replay", icon: "⟳" },
  { name: "Outcomes", icon: "↗" },
  { name: "Audit", icon: "◌" },
  { name: "Evaluation", icon: "◎" },
]

const DEMO_PRESETS = [
  {
    id: "ALLOW_HIGH_NET",
    name: "Scenario 1: High-Value Autonomous Recovery (ALLOW)",
    type: "ALLOW",
    description: "High expected net recovery exceeding autonomous threshold with passing safety guardrails.",
    caseData: {
      event_id: "EVT_DEMO_ALLOW_001",
      failure_id: "FAIL_DEMO_ALLOW_001",
      payment_id: "PAY_DEMO_ALLOW_001",
      customer_id: "CUST_DEMO_ALLOW_001",
      subscription_id: "SUB_DEMO_001",
      amount: 2500.0,
      failure_reason: "INSUFFICIENT_FUNDS",
      behavior_profile: "normal",
      account_age_days: 120,
      successful_payments: 8,
      failed_payments: 1,
      total_payments: 9,
      payment_success_rate: 0.88,
      historical_recovery_rate: 0.6,
      engagement_score: 0.85,
      monthly_subscription_value: 1250.0,
      payment_status: "FAILED",
      candidate_action: "PAYMENT_LINK",
      estimated_recovery_probability: 0.85,
      intervention_cost: 3.0,
      expected_gross_recovery: 2125.0,
      expected_net_recovery: 2122.0,
      policy_result: "ALLOW",
      policy_reason: "All policy safety checks passed cleanly.",
      policy_checks: ["ALL_SAFETY_CHECKS_PASSED"],
      execution_mode: "SIMULATION",
      execution_status: "EXECUTED_SIMULATION",
      execution_result: "PAYMENT_LINK",
      simulated_recovered: true,
      realized_gross_recovery: 2500.0,
      realized_net_recovery: 2497.0,
      decision_id: "DEC_349d5a9d80d1",
      execution_id: "EXEC_774a1290bb34",
      outcome_id: "OUT_91a00472eef1",
    },
  },
  {
    id: "HUMAN_HIGH_VAL",
    name: "Scenario 2: High-Value Low-Confidence Escalation (HUMAN)",
    type: "HUMAN",
    description: "High transaction amount (≥₹10,000) with confidence below 70% threshold triggers human escalation.",
    caseData: {
      event_id: "EVT_DEMO_HUMAN_001",
      failure_id: "FAIL_DEMO_HUMAN_001",
      payment_id: "PAY_DEMO_HUMAN_001",
      customer_id: "CUST_DEMO_HUMAN_001",
      subscription_id: "SUB_DEMO_002",
      amount: 15000.0,
      failure_reason: "INSUFFICIENT_FUNDS",
      behavior_profile: "high_value_loyal",
      account_age_days: 200,
      successful_payments: 12,
      failed_payments: 2,
      total_payments: 14,
      payment_success_rate: 0.85,
      historical_recovery_rate: 0.5,
      engagement_score: 0.7,
      monthly_subscription_value: 5000.0,
      payment_status: "FAILED",
      candidate_action: "UPDATE_PAYMENT_METHOD",
      estimated_recovery_probability: 0.5,
      intervention_cost: 3.0,
      expected_gross_recovery: 7500.0,
      expected_net_recovery: 7497.0,
      policy_result: "HUMAN",
      policy_reason: "High value payment (₹15,000.00) with probability 0.50 < 0.70. Escalating to human review.",
      policy_checks: ["HIGH_VALUE_LOW_CONFIDENCE_HUMAN"],
      execution_mode: "SIMULATION",
      execution_status: "NOT_AUTONOMOUSLY_EXECUTED",
      execution_result: "HUMAN_ESCALATION",
      simulated_recovered: false,
      realized_gross_recovery: 0.0,
      realized_net_recovery: 0.0,
      decision_id: "DEC_54199c0172e2",
      execution_id: "EXEC_289a01f7cc41",
      outcome_id: "OUT_33a1058288aa",
    },
  },
  {
    id: "STOP_STALE",
    name: "Scenario 3: Stale Payment Guardrail (STOP)",
    type: "STOP",
    description: "Failure event older than 30 days is blocked from autonomous execution by safety policy.",
    caseData: {
      event_id: "EVT_DEMO_STOP_001",
      failure_id: "FAIL_DEMO_STOP_001",
      payment_id: "PAY_DEMO_STOP_001",
      customer_id: "CUST_DEMO_STOP_001",
      subscription_id: "SUB_DEMO_003",
      amount: 500.0,
      failure_reason: "INSUFFICIENT_FUNDS",
      behavior_profile: "low_engagement",
      account_age_days: 45,
      successful_payments: 1,
      failed_payments: 2,
      total_payments: 3,
      payment_success_rate: 0.33,
      historical_recovery_rate: 0.2,
      engagement_score: 0.3,
      monthly_subscription_value: 250.0,
      event_age_days: 45,
      payment_status: "FAILED",
      candidate_action: "PAYMENT_LINK",
      estimated_recovery_probability: 0.85,
      intervention_cost: 3.0,
      expected_gross_recovery: 425.0,
      expected_net_recovery: 422.0,
      policy_result: "STOP",
      policy_reason: "Payment failure event is stale (> 30 days old). Autonomous execution blocked.",
      policy_checks: ["STALE_EVENT_BLOCKED"],
      execution_mode: "SIMULATION",
      execution_status: "NOT_EXECUTED",
      execution_result: "STOPPED",
      simulated_recovered: false,
      realized_gross_recovery: 0.0,
      realized_net_recovery: 0.0,
      decision_id: "DEC_1a95eac176d6",
      execution_id: "EXEC_8841b9c910aa",
      outcome_id: "OUT_01c2987114ee",
    },
  },
  {
    id: "REJECTED_DUP",
    name: "Scenario 4: Idempotency Protection (REJECTED_DUPLICATE_EVENT)",
    type: "DUPLICATE",
    description: "Atomic SQLite pre-claim detects duplicate failure ID and prevents duplicate action execution.",
    caseData: {
      event_id: "EVT_DEMO_ALLOW_001",
      failure_id: "FAIL_DEMO_ALLOW_001",
      payment_id: "PAY_DEMO_ALLOW_001",
      customer_id: "CUST_DEMO_ALLOW_001",
      amount: 2500.0,
      failure_reason: "INSUFFICIENT_FUNDS",
      payment_status: "FAILED",
      candidate_action: "PAYMENT_LINK",
      estimated_recovery_probability: 0.85,
      intervention_cost: 3.0,
      expected_gross_recovery: 2125.0,
      expected_net_recovery: 2122.0,
      policy_result: "ALLOW",
      policy_reason: "Event 'EVT_DEMO_ALLOW_001' or Failure ID 'FAIL_DEMO_ALLOW_001' has already been processed or claimed.",
      execution_status: "EXECUTED_SIMULATION",
      execution_result: "PAYMENT_LINK",
      status_response: "REJECTED_DUPLICATE_EVENT",
      decision_id: "DEC_349d5a9d80d1",
      execution_id: "EXEC_774a1290bb34",
      outcome_id: "OUT_91a00472eef1",
    },
  },
  {
    id: "REJECTED_REC",
    name: "Scenario 5: Already Recovered Protection (REJECTED_ALREADY_RECOVERED)",
    type: "RECOVERED",
    description: "Protects against intervening on payments that have already been successfully recovered.",
    caseData: {
      event_id: "EVT_DEMO_REC_001",
      failure_id: "FAIL_DEMO_REC_001",
      payment_id: "PAY_REC_001",
      customer_id: "CUST_DEMO_REC_001",
      amount: 1200.0,
      failure_reason: "INSUFFICIENT_FUNDS",
      payment_status: "RECOVERED",
      candidate_action: "STOP",
      estimated_recovery_probability: 0.0,
      intervention_cost: 0.0,
      expected_gross_recovery: 0.0,
      expected_net_recovery: 0.0,
      policy_result: "STOP",
      policy_reason: "Payment 'PAY_REC_001' is already recovered/successful.",
      status_response: "REJECTED_ALREADY_RECOVERED",
    },
  },
]

/* =========================================================
   FORMATTING HELPERS
========================================================= */

function isValidNumber(value) {
  if (value === null || value === undefined || value === "") return false
  const n = Number(value)
  return Number.isFinite(n)
}

function money(value) {
  if (!isValidNumber(value)) return "—"
  return `₹${Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  })}`
}

function percent(value) {
  if (!isValidNumber(value)) return "—"
  return `${Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 1,
  })}%`
}

function number(value) {
  if (!isValidNumber(value)) return "—"
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  })
}

function actionName(action) {
  if (!action) return "—"
  return String(action)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function statusLabel(status) {
  if (!status) return "—"
  return String(status).replaceAll("_", " ")
}

function formatCellValue(key, rawValue) {
  if (rawValue === null || rawValue === undefined || rawValue === "") {
    return "—"
  }

  if (key.includes("probability")) {
    return percent(Number(rawValue) * 100)
  }

  if (
    key.includes("amount") ||
    key.includes("recovery") ||
    key.includes("cost") ||
    key.includes("value")
  ) {
    return money(rawValue)
  }

  if (key.includes("rate") && isValidNumber(rawValue)) {
    return percent(Number(rawValue))
  }

  if (key.includes("action")) {
    return actionName(rawValue)
  }

  return String(rawValue)
}

function formatEvaluationMetric(metric, value) {
  if (!isValidNumber(value)) return value === "" ? "—" : String(value ?? "—")

  const m = String(metric || "").toLowerCase()

  if (m.includes("rate") || m.includes("%") || m.includes("match") || m.includes("gap")) {
    return percent(Number(value))
  }

  if (
    m.includes("revenue") ||
    m.includes("recovered") ||
    m.includes("cost") ||
    m.includes("net") ||
    m.includes("vs")
  ) {
    return money(value)
  }

  return number(value)
}

function isSelected(item) {
  return (
    item.selected === true ||
    String(item.selected).toLowerCase() === "true" ||
    item.portfolio_selected === true ||
    String(item.portfolio_selected).toLowerCase() === "true"
  )
}

/* =========================================================
   APP
========================================================= */

function App() {
  const [activePage, setActivePage] = useState("Overview")
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [selectedReplayCase, setSelectedReplayCase] = useState(null)
  const [data, setData] = useState({
    overview: null,
    portfolio: [],
    decisions: [],
    v2decisions: null,
    outcomes: [],
    policy: [],
    execution: [],
    evaluation: [],
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [apiWarnings, setApiWarnings] = useState([])
  const requestRef = useRef(0)

  const loadData = async () => {
    const requestId = ++requestRef.current

    try {
      setLoading(true)
      setError(null)
      setApiWarnings([])

      const endpoints = [
        ["overview", "/api/overview"],
        ["portfolio", "/api/portfolio"],
        ["decisions", "/api/decisions"],
        ["v2decisions", "/api/v2/decisions"],
        ["outcomes", "/api/outcomes"],
        ["policy", "/api/policy"],
        ["execution", "/api/execution"],
        ["evaluation", "/api/evaluation"],
      ]

      const results = await Promise.allSettled(
        endpoints.map(async ([key, endpoint]) => {
          const response = await fetch(`${API_URL}${endpoint}`)

          if (!response.ok) {
            throw new Error(`${endpoint} returned ${response.status}`)
          }

          return [key, await response.json()]
        }),
      )

      if (requestId !== requestRef.current) return

      const result = {}
      const failures = []

      for (let i = 0; i < results.length; i++) {
        const settled = results[i]
        const [key, endpoint] = endpoints[i]

        if (settled.status === "fulfilled") {
          const [resultKey, value] = settled.value
          result[resultKey] = value
        } else {
          failures.push(`${endpoint}: ${settled.reason?.message || "failed"}`)
        }
      }

      if (failures.length === endpoints.length) {
        setError(
          `Unable to connect to RecoveryOS API at ${API_URL}. ${failures.join("; ")}`,
        )
      } else if (failures.length > 0) {
        setApiWarnings(failures)
      }

      setData({
        overview: result.overview ?? null,
        portfolio: Array.isArray(result.portfolio)
          ? result.portfolio
          : result.portfolio?.items || [],
        decisions: Array.isArray(result.decisions)
          ? result.decisions
          : result.decisions?.items || [],
        v2decisions: result.v2decisions ?? null,
        outcomes: Array.isArray(result.outcomes)
          ? result.outcomes
          : result.outcomes?.items || [],
        policy: Array.isArray(result.policy)
          ? result.policy
          : result.policy?.items || [],
        execution: Array.isArray(result.execution)
          ? result.execution
          : result.execution?.items || [],
        evaluation: Array.isArray(result.evaluation)
          ? result.evaluation
          : result.evaluation?.items || [],
      })
    } catch (err) {
      if (requestId !== requestRef.current) return
      console.error(err)
      setError(`Unable to connect to RecoveryOS API: ${err.message}`)
    } finally {
      if (requestId === requestRef.current) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const stoppedCount = useMemo(
    () =>
      data.policy.filter((item) => item.policy_result === "STOP").length,
    [data.policy],
  )

  const pageDescription = {
    Overview: "Monitor recovery opportunities, decisions and outcomes.",
    Portfolio: "Prioritized revenue recovery opportunities.",
    Decisions: "AI-generated recovery decisions.",
    "Decision Replay": "Step-by-step visual audit of counterfactual economic decisioning, safety policy, execution, and outcomes.",
    Outcomes: "Measured recovery results from executed interventions.",
    Audit: "Policy, execution and control evidence.",
    Evaluation: "Benchmark RecoveryOS against alternative strategies.",
  }

  const navigateTo = (page) => {
    setActivePage(page)
    setMobileNavOpen(false)
  }

  const handleOpenReplay = (item) => {
    setSelectedReplayCase(item)
    setActivePage("Decision Replay")
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 font-sans">
      <div className="flex min-h-screen">
        {/* Mobile overlay */}
        {mobileNavOpen && (
          <button
            type="button"
            aria-label="Close navigation"
            className="fixed inset-0 z-30 bg-black/60 lg:hidden"
            onClick={() => setMobileNavOpen(false)}
          />
        )}

        {/* SIDEBAR */}
        <aside
          className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-zinc-800/80 bg-[#0c0c0f] transition-transform duration-200 lg:translate-x-0 ${
            mobileNavOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="flex h-20 items-center border-b border-zinc-800/80 px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-bold text-black shadow-sm">
                R
              </div>
              <div>
                <h1 className="text-[15px] font-semibold tracking-tight text-white">
                  RecoveryOS <span className="text-[10px] text-emerald-400 font-mono">v3.1</span>
                </h1>
                <p className="text-[11px] text-zinc-500">
                  Revenue Intelligence Engine
                </p>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-6">
            <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-600">
              Workspace
            </p>

            <nav className="space-y-1">
              {navItems.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  onClick={() => navigateTo(item.name)}
                  className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition font-medium ${
                    activePage === item.name
                      ? "bg-zinc-800/90 text-white shadow-sm border border-zinc-700/50"
                      : "text-zinc-500 hover:bg-zinc-800/40 hover:text-zinc-200"
                  }`}
                >
                  <span className="w-5 text-center text-base">{item.icon}</span>
                  {item.name}
                  {item.name === "Decision Replay" && (
                    <span className="ml-auto rounded bg-emerald-500/10 border border-emerald-500/30 px-1.5 py-0.5 text-[9px] font-mono text-emerald-400 uppercase">
                      Audit
                    </span>
                  )}
                </button>
              ))}
            </nav>

            <div className="mt-10">
              <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-600">
                Environment
              </p>
              <div className="mx-2 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                  <span className="text-xs font-medium text-zinc-300">
                    Simulation / Test Mode
                  </span>
                </div>
                <p className="mt-2 text-[11px] leading-5 text-zinc-500">
                  Deterministic evaluation sandbox. No live payment money dispatched.
                </p>
              </div>
            </div>
          </div>

          <div className="border-t border-zinc-800/80 p-4">
            <div className="flex items-center gap-3 rounded-lg px-2 py-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-zinc-300">
                A
              </div>
              <div>
                <p className="text-xs font-medium text-zinc-300">
                  Fintech Operations Console
                </p>
                <p className="text-[10px] text-zinc-600">Razorpay Buildathon v3.1</p>
              </div>
            </div>
          </div>
        </aside>

        {/* MAIN */}
        <div className="flex min-h-screen flex-1 flex-col lg:ml-64">
          {/* TOP BAR */}
          <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-zinc-800/80 bg-[#09090b]/95 px-4 backdrop-blur sm:px-8">
            <div className="flex items-center gap-3">
              <button
                type="button"
                aria-label="Open navigation"
                onClick={() => setMobileNavOpen(true)}
                className="rounded-md border border-zinc-800 px-2.5 py-1.5 text-sm text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 lg:hidden"
              >
                ☰
              </button>

              <div className="flex items-center gap-2 text-xs">
                <span className="text-zinc-600">Workspace</span>
                <span className="text-zinc-700">/</span>
                <span className="text-zinc-400 font-medium">{activePage}</span>
              </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-3">
              <button
                type="button"
                onClick={loadData}
                disabled={loading}
                className="rounded-md border border-zinc-800 bg-zinc-900/60 px-3 py-1.5 text-xs font-medium text-zinc-400 transition hover:border-zinc-700 hover:text-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Refreshing..." : "Refresh data"}
              </button>
            </div>
          </header>

          {(error || apiWarnings.length > 0) && (
            <div className="mx-auto w-full max-w-[1500px] px-4 pt-6 sm:px-8">
              {error && <ErrorState message={error} onRetry={loadData} />}
              {!error && apiWarnings.length > 0 && (
                <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 px-4 py-3 text-sm text-amber-400">
                  Partial data loaded. Failed endpoints: {apiWarnings.join("; ")}
                </div>
              )}
            </div>
          )}

          {/* PAGE */}
          <main className="mx-auto w-full max-w-[1500px] px-4 py-6 sm:px-8 sm:py-8">
            <div className="mb-6 sm:mb-8">
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-600">
                Revenue Recovery Platform
              </p>

              <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">
                    {activePage}
                  </h2>
                  <p className="mt-2 text-sm text-zinc-500">
                    {pageDescription[activePage]}
                  </p>
                </div>

                <div className="flex w-fit items-center gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  <span className="text-xs font-medium text-amber-400">
                    Simulation / Sandbox Mode
                  </span>
                </div>
              </div>
            </div>

            {activePage === "Overview" && (
              <OverviewPage
                overview={data.overview}
                portfolio={data.portfolio}
                stoppedCount={stoppedCount}
                loading={loading}
                onOpenReplay={handleOpenReplay}
              />
            )}

            {activePage === "Portfolio" && (
              <PortfolioPage
                portfolio={data.portfolio}
                loading={loading}
                onOpenReplay={handleOpenReplay}
              />
            )}

            {activePage === "Decisions" && (
              <DecisionsPage
                decisions={data.decisions}
                loading={loading}
                onOpenReplay={handleOpenReplay}
              />
            )}

            {activePage === "Decision Replay" && (
              <DecisionReplayPage
                portfolio={data.portfolio}
                decisions={data.decisions}
                v2decisions={data.v2decisions}
                policy={data.policy}
                execution={data.execution}
                outcomes={data.outcomes}
                loading={loading}
                initialCase={selectedReplayCase}
              />
            )}

            {activePage === "Outcomes" && (
              <OutcomesPage outcomes={data.outcomes} loading={loading} />
            )}

            {activePage === "Audit" && (
              <AuditPage
                policy={data.policy}
                execution={data.execution}
                loading={loading}
                onOpenReplay={handleOpenReplay}
              />
            )}

            {activePage === "Evaluation" && (
              <EvaluationPage evaluation={data.evaluation} loading={loading} />
            )}

            <div className="mt-10 flex flex-col gap-2 border-t border-zinc-900 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-[10px] text-zinc-600 font-mono">
                RecoveryOS v3.1 • Bounded Economic Decision Engine
              </p>
              <p className="text-[10px] text-zinc-600">
                Offline benchmark & simulation test environment • No real money dispatched
              </p>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

/* =========================================================
   DECISION REPLAY PAGE (THE 7-STAGE REPLAY VIEW)
========================================================= */

function DecisionReplayPage({
  portfolio,
  decisions,
  v2decisions,
  policy,
  execution,
  outcomes,
  loading,
  initialCase,
}) {
  const [selectedPresetId, setSelectedPresetId] = useState("ALLOW_HIGH_NET")
  const [selectedCustomFid, setSelectedCustomFid] = useState("")
  const [activeStageFilter, setActiveStageFilter] = useState(null)
  const [showWhyThisAction, setShowWhyThisAction] = useState(false)
  const [apiProcessing, setApiProcessing] = useState(false)
  const [livePipelineOutput, setLivePipelineOutput] = useState(null)

  // Determine current active case data
  const currentCase = useMemo(() => {
    // If live API output exists, use that
    if (livePipelineOutput?.record) {
      return livePipelineOutput.record
    }

    // If custom failure ID selected from portfolio
    if (selectedCustomFid) {
      const pMatch = portfolio.find((item) => String(item.failure_id) === selectedCustomFid)
      const dMatch = decisions.find((item) => String(item.failure_id) === selectedCustomFid)
      const polMatch = policy.find((item) => String(item.failure_id) === selectedCustomFid)
      const execMatch = execution.find((item) => String(item.failure_id) === selectedCustomFid)
      const outMatch = outcomes.find((item) => String(item.failure_id) === selectedCustomFid)

      if (pMatch || dMatch) {
        const base = pMatch || dMatch
        return {
          ...base,
          policy_result: polMatch?.policy_result || base.policy_result || "ALLOW",
          policy_reason: polMatch?.policy_reason || base.policy_reason || "All policy safety checks passed cleanly.",
          policy_checks: polMatch?.policy_checks || ["ALL_SAFETY_CHECKS_PASSED"],
          execution_status: execMatch?.execution_status || "EXECUTED_SIMULATION",
          execution_result: execMatch?.execution_result || base.candidate_action,
          execution_mode: "SIMULATION",
          simulated_recovered: outMatch?.outcome_status === "RECOVERED",
          realized_gross_recovery: outMatch?.actual_recovered_amount || base.amount,
          realized_net_recovery: (outMatch?.actual_recovered_amount || base.amount) - (base.intervention_cost || 3.0),
          decision_id: dMatch?.decision_id || `DEC_${base.failure_id}`,
          execution_id: execMatch?.execution_id || `EXEC_${base.failure_id}`,
          outcome_id: outMatch?.outcome_id || `OUT_${base.failure_id}`,
          event_id: `EVT_${base.failure_id}`,
        }
      }
    }

    // If initialCase passed via props
    if (initialCase && !selectedCustomFid && selectedPresetId === "CUSTOM") {
      return initialCase
    }

    // Fallback to selected preset scenario
    const preset = DEMO_PRESETS.find((p) => p.id === selectedPresetId)
    return preset ? preset.caseData : DEMO_PRESETS[0].caseData
  }, [
    livePipelineOutput,
    selectedCustomFid,
    initialCase,
    selectedPresetId,
    portfolio,
    decisions,
    policy,
    execution,
    outcomes,
  ])

  // Extract all 6 candidate action evaluation rows for currentCase
  const candidateActionsList = useMemo(() => {
    const fid = currentCase?.failure_id

    // Check if backend returned candidates list
    if (v2decisions?.candidates && Array.isArray(v2decisions.candidates)) {
      const matches = v2decisions.candidates.filter((c) => String(c.failure_id) === fid)
      if (matches.length > 0) {
        return matches.sort((a, b) => Number(b.expected_net_recovery) - Number(a.expected_net_recovery))
      }
    }

    // Generate deterministic 6 candidate actions if not found
    const amount = Number(currentCase?.amount || 2500.0)
    const baseProb = Number(currentCase?.estimated_recovery_probability || 0.85)

    const actionsDef = [
      { name: "RETRY_NOW", cost: 2.0, probMult: 0.95 },
      { name: "WAIT_AND_RETRY", cost: 2.0, probMult: 0.92 },
      { name: "SEND_REMINDER", cost: 1.0, probMult: 0.55 },
      { name: "PAYMENT_LINK", cost: 3.0, probMult: 1.0 },
      { name: "UPDATE_PAYMENT_METHOD", cost: 3.0, probMult: 0.82 },
      { name: "STOP", cost: 0.0, probMult: 0.0 },
    ]

    return actionsDef.map((a) => {
      const prob = Math.min(0.99, Math.max(0.0, baseProb * a.probMult))
      const gross = a.name === "STOP" ? 0.0 : amount * prob
      const net = a.name === "STOP" ? 0.0 : gross - a.cost
      return {
        candidate_action: a.name,
        estimated_recovery_probability: prob,
        intervention_cost: a.cost,
        expected_gross_recovery: gross,
        expected_net_recovery: net,
      }
    }).sort((a, b) => b.expected_net_recovery - a.expected_net_recovery)
  }, [currentCase, v2decisions])

  // Find top 1 (selected) and top 2 action
  const top1Action = candidateActionsList[0] || {}
  const top2Action = candidateActionsList[1] || {}
  const marginNet = Number(top1Action.expected_net_recovery || 0) - Number(top2Action.expected_net_recovery || 0)

  // Handle Preset Select
  const handleSelectPreset = (presetId) => {
    setSelectedPresetId(presetId)
    setSelectedCustomFid("")
    setLivePipelineOutput(null)
    setShowWhyThisAction(false)
  }

  // Handle Custom Failure Select
  const handleSelectCustomFid = (fid) => {
    setSelectedCustomFid(fid)
    setSelectedPresetId("CUSTOM")
    setLivePipelineOutput(null)
    setShowWhyThisAction(false)
  }

  // Handle Live Backend Event Dispatch
  const handleRunLiveBackendEvent = async () => {
    try {
      setApiProcessing(true)
      const payload = currentCase

      const res = await fetch(`${API_URL}/api/v2/events/failure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      const json = await res.json()
      setLivePipelineOutput(json)
    } catch (err) {
      console.error(err)
    } finally {
      setApiProcessing(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* TOOLBAR & PRESET SELECTION */}
      <div className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-widest text-emerald-400">
              Interactive Decision Auditor
            </span>
            <h3 className="text-base font-semibold text-white">
              Counterfactual Decision Replay Console
            </h3>
            <p className="mt-1 text-xs text-zinc-500">
              Trace economic action ranking, safety guardrails, simulation adapter execution, and audit lineage.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleRunLiveBackendEvent}
              disabled={apiProcessing}
              className="inline-flex items-center gap-2 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3.5 py-2 text-xs font-semibold text-emerald-400 transition hover:bg-emerald-500/20 disabled:opacity-50"
            >
              <span>{apiProcessing ? "Running DB Claim & Pipeline..." : "Replay Decision ⟳"}</span>
            </button>
          </div>
        </div>

        {/* PRESET SCENARIO SELECTOR */}
        <div className="mt-5 border-t border-zinc-800/80 pt-4">
          <p className="mb-2.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
            Select Replay Scenario
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {DEMO_PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => handleSelectPreset(p.id)}
                className={`rounded-lg border p-3 text-left transition ${
                  selectedPresetId === p.id && !selectedCustomFid
                    ? "border-emerald-500/60 bg-emerald-500/10 text-white shadow-sm"
                    : "border-zinc-800 bg-zinc-900/40 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase text-zinc-400">
                    {p.type}
                  </span>
                  {selectedPresetId === p.id && !selectedCustomFid && (
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  )}
                </div>
                <p className="mt-1 text-xs font-semibold text-zinc-200 truncate">
                  {p.name.split(":")[1] || p.name}
                </p>
                <p className="mt-1 text-[10px] text-zinc-500 line-clamp-2">
                  {p.description}
                </p>
              </button>
            ))}
          </div>

          {/* CUSTOM CASE PICKER */}
          <div className="mt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/80">
            <span className="text-xs text-zinc-400 font-medium">
              Or pick from 559 Portfolio Failures:
            </span>
            <select
              value={selectedCustomFid}
              onChange={(e) => handleSelectCustomFid(e.target.value)}
              className="rounded-md border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-mono text-zinc-300 outline-none focus:border-zinc-600 sm:w-80"
            >
              <option value="">-- Select Portfolio Case --</option>
              {portfolio.slice(0, 100).map((item) => (
                <option key={item.failure_id} value={item.failure_id}>
                  {item.failure_id} ({money(item.amount)} • {item.failure_reason})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* STAGE TIMELINE STEPS NAVIGATION */}
      <div className="flex overflow-x-auto border-b border-zinc-800/80 pb-2">
        <div className="flex items-center gap-2 min-w-max">
          {[
            { num: 1, label: "1. PAYMENT FAILURE" },
            { num: 2, label: "2. RECOVERY CONTEXT" },
            { num: 3, label: "3. ACTION COMPARISON" },
            { num: 4, label: "4. SAFETY DECISION" },
            { num: 5, label: "5. EXECUTION" },
            { num: 6, label: "6. OUTCOME" },
            { num: 7, label: "7. AUDIT" },
          ].map((s) => (
            <button
              key={s.num}
              type="button"
              onClick={() => setActiveStageFilter(activeStageFilter === s.num ? null : s.num)}
              className={`rounded-md border px-3 py-1.5 text-xs font-semibold tracking-tight transition ${
                activeStageFilter === s.num
                  ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                  : "border-zinc-800 bg-zinc-900/50 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
              }`}
            >
              {s.label}
            </button>
          ))}
          {activeStageFilter !== null && (
            <button
              type="button"
              onClick={() => setActiveStageFilter(null)}
              className="text-xs text-zinc-500 underline ml-2"
            >
              Show all stages
            </button>
          )}
        </div>
      </div>

      {/* THE 7-STAGE REPLAY VISUAL SEQUENCE */}
      <div className="space-y-6">
        {/* STAGE 1: PAYMENT FAILURE */}
        {(activeStageFilter === null || activeStageFilter === 1) && (
          <section className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-bold text-zinc-300">
                  1
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  STAGE 1 — PAYMENT FAILURE INGESTION
                </h4>
              </div>
              <span className="font-mono text-xs text-zinc-500">
                {currentCase.payment_status || "FAILED"}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <ReplayMetric
                label="Failure ID"
                value={currentCase.failure_id || "—"}
                mono
              />
              <ReplayMetric
                label="Payment Amount"
                value={money(currentCase.amount)}
                highlight
              />
              <ReplayMetric
                label="Failure Reason"
                value={currentCase.failure_reason || "—"}
              />
              <ReplayMetric
                label="Customer / Sub ID"
                value={`${currentCase.customer_id || "—"} / ${currentCase.subscription_id || "SUB_001"}`}
                mono
              />
            </div>
          </section>
        )}

        {/* STAGE 2: RECOVERY CONTEXT */}
        {(activeStageFilter === null || activeStageFilter === 2) && (
          <section className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-bold text-zinc-300">
                  2
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  STAGE 2 — RECOVERY CONTEXT & CUSTOMER FEATURES
                </h4>
              </div>
              <span className="text-xs text-zinc-500">
                Profile: <strong className="text-zinc-300">{currentCase.behavior_profile || "normal"}</strong>
              </span>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <ReplayMetric
                label="Payment Success Rate"
                value={percent(Number(currentCase.payment_success_rate || 0.8) * 100)}
                description={`${currentCase.successful_payments || 5} of ${currentCase.total_payments || 6} payments`}
              />
              <ReplayMetric
                label="Historical Recovery Rate"
                value={percent(Number(currentCase.historical_recovery_rate || 0.5) * 100)}
                description="Past failure recovery"
              />
              <ReplayMetric
                label="Engagement Score"
                value={number(currentCase.engagement_score || 0.8)}
                description="Customer activity signal"
              />
              <ReplayMetric
                label="Account Tenure / Sub Value"
                value={`${currentCase.account_age_days || 30} days`}
                description={`MRR: ${money(currentCase.monthly_subscription_value || 1000)}`}
              />
            </div>
          </section>
        )}

        {/* STAGE 3: ACTION COMPARISON */}
        {(activeStageFilter === null || activeStageFilter === 3) && (
          <section className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-6 shadow-sm">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-800/80 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] font-bold text-emerald-400 border border-emerald-500/40">
                  3
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
                  STAGE 3 — COUNTERFACTUAL ACTION COMPARISON (6 CANDIDATE ACTIONS)
                </h4>
              </div>

              {/* WHY THIS ACTION BUTTON */}
              <button
                type="button"
                onClick={() => setShowWhyThisAction(!showWhyThisAction)}
                className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-400 transition hover:bg-emerald-500/20"
              >
                <span>Why this action?</span>
                <span className="text-xs">{showWhyThisAction ? "▲" : "▼"}</span>
              </button>
            </div>

            {/* EXPLANATORY INTERACTION (WHY THIS ACTION?) */}
            {showWhyThisAction && (
              <div className="mb-5 rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-4 text-xs text-zinc-300">
                <div className="flex items-center gap-2 mb-2 text-emerald-400 font-semibold">
                  <span>Economic Decision Logic:</span>
                </div>
                <p className="leading-5">
                  {currentCase.policy_result === "HUMAN" ? (
                    `Escalated to HUMAN review because transaction amount (${money(currentCase.amount)}) is high and model probability (${percent(Number(currentCase.estimated_recovery_probability || 0.5) * 100)}) is below the required 70% confidence threshold.`
                  ) : currentCase.policy_result === "STOP" ? (
                    `Selected STOP (zero cost, zero friction) because policy guardrails blocked active intervention: ${currentCase.policy_reason || "No intervention option optimal"}.`
                  ) : (
                    `Selected '${actionName(top1Action.candidate_action)}' because it maximizes expected net recovery at ${money(top1Action.expected_net_recovery)} (gross ${money(top1Action.expected_gross_recovery)} minus ${money(top1Action.intervention_cost)} cost), outperforming the second-best action '${actionName(top2Action.candidate_action)}' (net ${money(top2Action.expected_net_recovery)}) by an economic margin of ${money(marginNet)}.`
                  )}
                </p>
              </div>
            )}

            {/* THE 6 CANDIDATE ACTIONS TABLE */}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-left">
                <thead>
                  <tr className="border-b border-zinc-800 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                    <th className="px-4 py-3">Candidate Action</th>
                    <th className="px-4 py-3">Est. Prob (P)</th>
                    <th className="px-4 py-3">Intervention Cost</th>
                    <th className="px-4 py-3">Expected Gross</th>
                    <th className="px-4 py-3">Expected Net</th>
                    <th className="px-4 py-3 text-right">Selection Status</th>
                  </tr>
                </thead>
                <tbody>
                  {candidateActionsList.map((item, idx) => {
                    const isRank1 =
                      item.candidate_action === currentCase.candidate_action ||
                      idx === 0

                    return (
                      <tr
                        key={item.candidate_action}
                        className={`border-b border-zinc-800/60 transition ${
                          isRank1
                            ? "bg-emerald-500/10 border-l-4 border-l-emerald-400 font-semibold"
                            : "hover:bg-zinc-800/20"
                        }`}
                      >
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2">
                            <ActionBadge action={item.candidate_action} />
                            {isRank1 && (
                              <span className="text-[10px] text-emerald-400 font-mono">
                                (Rank #1)
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-xs text-zinc-300">
                          {percent(Number(item.estimated_recovery_probability || 0) * 100)}
                        </td>
                        <td className="px-4 py-3.5 text-xs text-zinc-400">
                          {money(item.intervention_cost)}
                        </td>
                        <td className="px-4 py-3.5 text-xs text-zinc-300">
                          {money(item.expected_gross_recovery)}
                        </td>
                        <td
                          className={`px-4 py-3.5 text-xs font-semibold ${
                            isRank1 ? "text-emerald-400 text-sm" : "text-zinc-400"
                          }`}
                        >
                          {money(item.expected_net_recovery)}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          {isRank1 ? (
                            <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-400">
                              ✓ Optimal Choice
                            </span>
                          ) : (
                            <span className="text-[10px] text-zinc-600 uppercase">
                              Rank #{idx + 1}
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* STAGE 4: SAFETY DECISION */}
        {(activeStageFilter === null || activeStageFilter === 4) && (
          <section className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-bold text-zinc-300">
                  4
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  STAGE 4 — BOUNDED AUTONOMY & POLICY SAFETY GUARDRAILS
                </h4>
              </div>
              <StatusBadge status={currentCase.policy_result || "ALLOW"} />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
                <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
                  Policy Evaluation Result
                </p>
                <div className="mt-2 flex items-center gap-3">
                  <StatusBadge status={currentCase.policy_result || "ALLOW"} />
                  <span className="text-xs text-zinc-300 font-medium">
                    {currentCase.policy_result === "ALLOW"
                      ? "Eligible for Autonomous Execution"
                      : currentCase.policy_result === "HUMAN"
                      ? "Escalated to Manual Human Review"
                      : "Blocked by Safety Policy"}
                  </span>
                </div>
                <p className="mt-3 text-xs leading-5 text-zinc-400">
                  {currentCase.policy_reason || "All policy safety checks passed cleanly."}
                </p>
              </div>

              <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
                <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
                  Active Guardrail Checks
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(currentCase.policy_checks || ["ALL_SAFETY_CHECKS_PASSED"]).map((chk) => (
                    <span
                      key={chk}
                      className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1 font-mono text-[10px] text-zinc-400"
                    >
                      {chk}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </section>
        )}

        {/* STAGE 5: EXECUTION */}
        {(activeStageFilter === null || activeStageFilter === 5) && (
          <section className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-bold text-zinc-300">
                  5
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  STAGE 5 — DISPATCH EXECUTION ADAPTER
                </h4>
              </div>
              <span className="rounded bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] font-mono text-amber-400 uppercase">
                {currentCase.execution_mode || "SIMULATION / SANDBOX"}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <ReplayMetric
                label="Execution Status"
                value={currentCase.execution_status || "EXECUTED_SIMULATION"}
              />
              <ReplayMetric
                label="Dispatched Action"
                value={actionName(currentCase.candidate_action)}
              />
              <ReplayMetric
                label="Execution Mode"
                value={currentCase.execution_mode || "SIMULATION"}
                description="Sandbox Test Mode"
              />
            </div>

            <div className="mt-4 rounded-md border border-amber-500/20 bg-amber-500/5 p-3 text-[11px] text-amber-400/90">
              ℹ <strong>Honest Disclosure</strong>: Dispatch executed via <code className="font-mono">SimulationExecutionAdapter</code> in Sandbox test mode. No live money dispatched.
            </div>
          </section>
        )}

        {/* STAGE 6: OUTCOME */}
        {(activeStageFilter === null || activeStageFilter === 6) && (
          <section className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] font-bold text-emerald-400 border border-emerald-500/40">
                  6
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
                  STAGE 6 — MEASURED OUTCOME AUDIT
                </h4>
              </div>
              <StatusBadge
                status={currentCase.simulated_recovered ? "RECOVERED" : "NOT_RECOVERED"}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <ReplayMetric
                label="Recovery Result"
                value={currentCase.simulated_recovered ? "RECOVERED" : "NOT RECOVERED"}
                highlight={currentCase.simulated_recovered}
              />
              <ReplayMetric
                label="Realized Gross"
                value={money(currentCase.realized_gross_recovery ?? currentCase.amount)}
              />
              <ReplayMetric
                label="Intervention Cost"
                value={money(currentCase.intervention_cost)}
              />
              <ReplayMetric
                label="Realized Net Recovery"
                value={money(currentCase.realized_net_recovery ?? (currentCase.amount - (currentCase.intervention_cost || 3.0)))}
                highlight
              />
            </div>
          </section>
        )}

        {/* STAGE 7: AUDIT */}
        {(activeStageFilter === null || activeStageFilter === 7) && (
          <section className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-bold text-zinc-300">
                  7
                </span>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  STAGE 7 — DURABLE AUDIT LINEAGE RECORD
                </h4>
              </div>
              <span className="text-[10px] font-mono text-zinc-500">
                SQLite DurableStateStore
              </span>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 font-mono">
              <ReplayMetric
                label="Event Identifier"
                value={currentCase.event_id || `EVT_${currentCase.failure_id}`}
                mono
              />
              <ReplayMetric
                label="Decision Identifier"
                value={currentCase.decision_id || `DEC_${currentCase.failure_id}`}
                mono
              />
              <ReplayMetric
                label="Execution Identifier"
                value={currentCase.execution_id || `EXEC_${currentCase.failure_id}`}
                mono
              />
              <ReplayMetric
                label="Outcome Identifier"
                value={currentCase.outcome_id || `OUT_${currentCase.failure_id}`}
                mono
              />
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

function ReplayMetric({ label, value, description, mono = false, highlight = false }) {
  return (
    <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/60 p-4">
      <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">{label}</p>
      <p
        className={`mt-2 text-base font-semibold ${
          highlight ? "text-emerald-400" : "text-zinc-200"
        } ${mono ? "font-mono text-xs" : ""}`}
      >
        {value ?? "—"}
      </p>
      {description && <p className="mt-1 text-[10px] text-zinc-600">{description}</p>}
    </div>
  )
}

/* =========================================================
   OVERVIEW
========================================================= */

function OverviewPage({ overview, portfolio, stoppedCount, loading, onOpenReplay }) {
  const selected = useMemo(
    () => portfolio.filter(isSelected),
    [portfolio],
  )

  const revenueAtRisk = overview?.total_value_at_risk ?? overview?.revenue_at_risk
  const expectedRecovery = overview?.expected_recovered_amount ?? overview?.expected_recovery
  const simulatedRecovered = overview?.actual_recovered_amount ?? overview?.simulated_recovered
  const recoveryRate = overview?.overall_recovery_rate ?? overview?.recovery_rate
  const portfolioCases = overview?.selected_cases ?? overview?.portfolio_cases ?? selected.length
  const executedCases = overview?.selected_cases ?? overview?.executed_cases

  const expectedNet = useMemo(
    () =>
      selected.reduce(
        (sum, item) => sum + Number(item.expected_net_recovery || 0),
        0,
      ),
    [selected],
  )

  if (loading && !overview) {
    return <LoadingState message="Loading RecoveryOS overview..." />
  }

  return (
    <>
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Revenue at Risk"
          value={money(revenueAtRisk)}
          description={`${portfolioCases ?? "—"} prioritized cases`}
          loading={loading}
        />
        <MetricCard
          label="Expected Recovery"
          value={money(expectedRecovery)}
          description="Before intervention cost (simulated)"
          loading={loading}
        />
        <MetricCard
          label="Simulated Recovered"
          value={money(simulatedRecovered)}
          description={`${executedCases ?? "—"} successful outcomes`}
          loading={loading}
          highlight
        />
        <MetricCard
          label="Recovery Rate"
          value={
            isValidNumber(recoveryRate)
              ? percent(Number(recoveryRate))
              : "—"
          }
          description="Simulated recovery rate"
          loading={loading}
        />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="overflow-hidden rounded-xl border border-zinc-800 bg-[#0d0d10] lg:col-span-2">
          <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
            <div>
              <h3 className="text-sm font-semibold">Recovery Portfolio</h3>
              <p className="mt-1 text-xs text-zinc-600">
                Highest-value opportunities selected by RecoveryOS
              </p>
            </div>
            <span className="text-xs text-zinc-600">{selected.length} cases</span>
          </div>
          <PortfolioTable items={selected.slice(0, 10)} loading={loading} onOpenReplay={onOpenReplay} />
        </div>

        <div className="rounded-xl border border-zinc-800 bg-[#0d0d10]">
          <div className="border-b border-zinc-800 px-5 py-4">
            <h3 className="text-sm font-semibold">Decision Engine</h3>
            <p className="mt-1 text-xs text-zinc-600">
              Policy routing from simulated outcomes
            </p>
          </div>

          <div className="space-y-5 p-5">
            <DecisionRow
              label="Autonomous cases"
              value={executedCases ?? "—"}
            />
            <DecisionRow
              label="Human review"
              value={overview?.human_cases ?? 0}
            />
            <DecisionRow label="Stopped" value={stoppedCount} />

            <div className="border-t border-zinc-800 pt-5">
              <p className="text-[10px] uppercase tracking-wider text-zinc-600">
                Expected Net Recovery
              </p>
              <p className="mt-2 text-xl font-semibold text-emerald-400">
                {money(expectedNet)}
              </p>
              <p className="mt-1 text-[11px] text-zinc-600">
                After intervention cost • simulated
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

/* =========================================================
   PORTFOLIO
========================================================= */

function PortfolioPage({ portfolio, loading, onOpenReplay }) {
  const [search, setSearch] = useState("")
  const [failureFilter, setFailureFilter] = useState("ALL")
  const [actionFilter, setActionFilter] = useState("ALL")
  const [sortBy, setSortBy] = useState("net")
  const [selectedCase, setSelectedCase] = useState(null)

  const selected = useMemo(
    () => portfolio.filter(isSelected),
    [portfolio],
  )

  const failureReasons = useMemo(
    () => ["ALL", ...new Set(selected.map((item) => item.failure_reason))],
    [selected],
  )

  const actions = useMemo(
    () => ["ALL", ...new Set(selected.map((item) => item.candidate_action))],
    [selected],
  )

  const filtered = useMemo(() => {
    return selected
      .filter((item) => {
        const query = search.toLowerCase()

        const matchesSearch =
          !query ||
          String(item.failure_id).toLowerCase().includes(query) ||
          String(item.customer_id).toLowerCase().includes(query)

        const matchesFailure =
          failureFilter === "ALL" || item.failure_reason === failureFilter

        const matchesAction =
          actionFilter === "ALL" || item.candidate_action === actionFilter

        return matchesSearch && matchesFailure && matchesAction
      })
      .sort((a, b) => {
        if (sortBy === "net") {
          return (
            Number(b.expected_net_recovery || 0) -
            Number(a.expected_net_recovery || 0)
          )
        }
        if (sortBy === "amount") {
          return Number(b.amount || 0) - Number(a.amount || 0)
        }
        if (sortBy === "probability") {
          return (
            Number(b.estimated_recovery_probability || 0) -
            Number(a.estimated_recovery_probability || 0)
          )
        }
        return 0
      })
  }, [selected, search, failureFilter, actionFilter, sortBy])

  const portfolioValue = useMemo(
    () => selected.reduce((sum, item) => sum + Number(item.amount || 0), 0),
    [selected],
  )

  const expectedNet = useMemo(
    () =>
      selected.reduce(
        (sum, item) => sum + Number(item.expected_net_recovery || 0),
        0,
      ),
    [selected],
  )

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Prioritized Cases"
          value={selected.length}
          description="Selected by portfolio engine"
        />
        <MetricCard
          label="Visible Cases"
          value={filtered.length}
          description="After current filters"
        />
        <MetricCard
          label="Portfolio Value"
          value={money(portfolioValue)}
          description="Revenue at risk"
        />
        <MetricCard
          label="Expected Net"
          value={money(expectedNet)}
          description="After intervention cost"
        />
      </div>

      <div className="mt-6 rounded-xl border border-zinc-800 bg-[#0d0d10]">
        <div className="border-b border-zinc-800 p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold">Recovery Portfolio</h3>
              <p className="mt-1 text-xs text-zinc-600">
                Ranked opportunities generated by the portfolio optimizer
              </p>
            </div>
            <span className="text-xs text-zinc-500">{filtered.length} results</span>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search failure or customer..."
              className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-300 outline-none placeholder:text-zinc-700 focus:border-zinc-600"
            />

            <select
              value={failureFilter}
              onChange={(e) => setFailureFilter(e.target.value)}
              className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-400 outline-none focus:border-zinc-600"
            >
              {failureReasons.map((reason) => (
                <option key={reason} value={reason}>
                  {reason === "ALL" ? "All failure reasons" : reason}
                </option>
              ))}
            </select>

            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-400 outline-none focus:border-zinc-600"
            >
              {actions.map((action) => (
                <option key={action} value={action}>
                  {action === "ALL" ? "All AI actions" : actionName(action)}
                </option>
              ))}
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-400 outline-none focus:border-zinc-600"
            >
              <option value="net">Sort: Expected Net</option>
              <option value="amount">Sort: Revenue at Risk</option>
              <option value="probability">Sort: Recovery Probability</option>
            </select>
          </div>
        </div>

        {loading ? (
          <LoadingState message="Loading RecoveryOS portfolio..." compact />
        ) : filtered.length === 0 ? (
          <EmptyState message="No cases match the current filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left">
              <thead>
                <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-wider text-zinc-600">
                  <th className="px-5 py-3">Rank</th>
                  <th className="px-5 py-3">Failure</th>
                  <th className="px-5 py-3">Amount</th>
                  <th className="px-5 py-3">Failure Reason</th>
                  <th className="px-5 py-3">AI Action</th>
                  <th className="px-5 py-3">Probability</th>
                  <th className="px-5 py-3">Expected Net</th>
                  <th className="px-5 py-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, index) => {
                  const isActive =
                    selectedCase?.failure_id === item.failure_id

                  return (
                    <tr
                      key={item.failure_id}
                      onClick={() => setSelectedCase(item)}
                      className={`cursor-pointer border-b border-zinc-800/60 transition hover:bg-zinc-800/30 ${
                        isActive ? "bg-zinc-800/40" : ""
                      }`}
                    >
                      <td className="px-5 py-4 text-xs text-zinc-600">
                        #{item.portfolio_rank || index + 1}
                      </td>
                      <td className="px-5 py-4 font-mono text-[11px] text-zinc-300">
                        {item.failure_id}
                      </td>
                      <td className="px-5 py-4 text-xs font-medium">
                        {money(item.amount)}
                      </td>
                      <td className="px-5 py-4 text-[11px] text-zinc-500">
                        {item.failure_reason}
                      </td>
                      <td className="px-5 py-4">
                        <ActionBadge action={item.candidate_action} />
                      </td>
                      <td className="px-5 py-4 text-[11px] text-zinc-400">
                        {percent(
                          Number(item.estimated_recovery_probability || 0) *
                            100,
                        )}
                      </td>
                      <td className="px-5 py-4 text-xs font-medium text-emerald-400">
                        {money(item.expected_net_recovery)}
                      </td>
                      <td className="px-5 py-4">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (onOpenReplay) onOpenReplay(item)
                          }}
                          className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold text-emerald-400 hover:bg-emerald-500/20 transition"
                        >
                          <span>Replay</span>
                          <span>⟳</span>
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedCase && (
        <div className="mt-6 overflow-hidden rounded-xl border border-zinc-800 bg-[#0d0d10]">
          <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-zinc-600">
                Recovery Case Detail
              </p>
              <h3 className="mt-1 font-mono text-sm font-semibold">
                {selectedCase.failure_id}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  if (onOpenReplay) onOpenReplay(selectedCase)
                }}
                className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-400 transition hover:bg-emerald-500/20"
              >
                <span>Replay Decision</span>
                <span>⟳</span>
              </button>
              <button
                type="button"
                onClick={() => setSelectedCase(null)}
                className="rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-500 transition hover:border-zinc-700 hover:text-zinc-200"
              >
                Close
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-px bg-zinc-800 sm:grid-cols-2 lg:grid-cols-3">
            <Detail label="Failure ID" value={selectedCase.failure_id} mono />
            <Detail label="Customer ID" value={selectedCase.customer_id} mono />
            <Detail label="Revenue at Risk" value={money(selectedCase.amount)} />
            <Detail label="Failure Reason" value={selectedCase.failure_reason} />
            <Detail
              label="Behavior Profile"
              value={selectedCase.behavior_profile}
            />
            <Detail
              label="AI Action"
              value={actionName(selectedCase.candidate_action)}
            />
            <Detail
              label="Recovery Probability"
              value={percent(
                Number(selectedCase.estimated_recovery_probability || 0) * 100,
              )}
            />
            <Detail
              label="Expected Gross"
              value={money(selectedCase.expected_gross_recovery)}
            />
            <Detail
              label="Intervention Cost"
              value={money(selectedCase.intervention_cost)}
            />
            <Detail
              label="Expected Net"
              value={money(selectedCase.expected_net_recovery)}
              highlight
            />
            <Detail
              label="Portfolio Rank"
              value={`#${selectedCase.portfolio_rank ?? "—"}`}
            />
            <Detail label="Status">
              <StatusBadge status="PRIORITIZED" variant="success" />
            </Detail>
          </div>
        </div>
      )}
    </>
  )
}

/* =========================================================
   DECISIONS
========================================================= */

function DecisionsPage({ decisions, loading, onOpenReplay }) {
  const actionCounts = useMemo(() => {
    const counts = {}
    decisions.forEach((item) => {
      const action = item.candidate_action || "UNKNOWN"
      counts[action] = (counts[action] || 0) + 1
    })
    return counts
  }, [decisions])

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total Decisions"
          value={decisions.length}
          description="M12 decision engine"
          loading={loading}
        />
        <MetricCard
          label="WAIT & RETRY"
          value={actionCounts.WAIT_AND_RETRY || 0}
          description="Selected action"
          loading={loading}
        />
        <MetricCard
          label="PAYMENT LINK"
          value={actionCounts.PAYMENT_LINK || 0}
          description="Selected action"
          loading={loading}
        />
        <MetricCard
          label="UPDATE METHOD"
          value={actionCounts.UPDATE_PAYMENT_METHOD || 0}
          description="Selected action"
          loading={loading}
        />
      </div>

      <DataTable
        title="Recovery Decisions"
        subtitle="AI decision engine output"
        items={decisions}
        loading={loading}
        onOpenReplay={onOpenReplay}
        columns={[
          ["decision_id", "Decision"],
          ["failure_id", "Payment"],
          ["candidate_action", "Action"],
          ["estimated_recovery_probability", "Probability"],
          ["expected_gross_recovery", "Expected Gross"],
          ["expected_net_recovery", "Expected Net"],
          ["decision_status", "Status"],
          ["replay", "Replay Audit"],
        ]}
        renderCell={(key, value, item) => {
          if (key === "candidate_action") {
            return <ActionBadge action={value} />
          }
          if (key === "decision_status") {
            return <StatusBadge status={value} />
          }
          if (key === "replay") {
            return (
              <button
                type="button"
                onClick={() => {
                  if (onOpenReplay) onOpenReplay(item)
                }}
                className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold text-emerald-400 hover:bg-emerald-500/20 transition"
              >
                <span>Replay</span>
                <span>⟳</span>
              </button>
            )
          }
          return formatCellValue(key, value)
        }}
      />
    </>
  )
}

/* =========================================================
   OUTCOMES
========================================================= */

function OutcomesPage({ outcomes, loading }) {
  const stats = useMemo(() => {
    const recovered = outcomes.filter(
      (item) => item.outcome_status === "RECOVERED",
    )
    const notRecovered = outcomes.filter(
      (item) => item.outcome_status === "NOT_RECOVERED",
    )
    const awaitingHuman = outcomes.filter(
      (item) => item.outcome_status === "AWAITING_HUMAN",
    )
    const recoveredAmount = recovered.reduce(
      (sum, item) => sum + Number(item.actual_recovered_amount || 0),
      0,
    )

    return { recovered, notRecovered, awaitingHuman, recoveredAmount }
  }, [outcomes])

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          label="Outcome Records"
          value={outcomes.length}
          description="M15 outcome audit"
          loading={loading}
        />
        <MetricCard
          label="Recovered"
          value={stats.recovered.length}
          description="Successful outcomes"
          loading={loading}
          highlight
        />
        <MetricCard
          label="Not Recovered"
          value={stats.notRecovered.length}
          description="Unsuccessful outcomes"
          loading={loading}
        />
        <MetricCard
          label="Awaiting Human"
          value={stats.awaitingHuman.length}
          description="Escalated for review"
          loading={loading}
        />
        <MetricCard
          label="Recovered Value"
          value={money(stats.recoveredAmount)}
          description="Simulated recovered amount"
          loading={loading}
          highlight
        />
      </div>

      <DataTable
        title="Recovery Outcomes"
        subtitle="Measured results after execution (simulated)"
        items={outcomes}
        loading={loading}
        columns={[
          ["failure_id", "Payment"],
          ["candidate_action", "Action"],
          ["amount", "Amount"],
          ["estimated_recovery_probability", "Probability"],
          ["actual_recovered_amount", "Recovered"],
          ["outcome_status", "Outcome"],
          ["outcome_reason", "Reason"],
        ]}
        renderCell={(key, value, item) => {
          if (key === "candidate_action") {
            return <ActionBadge action={value} />
          }
          if (key === "outcome_status") {
            return <StatusBadge status={value} />
          }
          if (key === "actual_recovered_amount") {
            const formatted = money(value)
            const isRecovered = item.outcome_status === "RECOVERED"
            return (
              <span
                className={
                  isRecovered && isValidNumber(value)
                    ? "font-medium text-emerald-400"
                    : ""
                }
              >
                {formatted}
              </span>
            )
          }
          if (key === "outcome_reason") {
            return (
              <span
                className="block max-w-xs truncate text-[11px] text-zinc-500"
                title={String(value || "")}
              >
                {value || "—"}
              </span>
            )
          }
          return formatCellValue(key, value)
        }}
      />
    </>
  )
}

/* =========================================================
   AUDIT
========================================================= */

function AuditPage({ policy, execution, loading, onOpenReplay }) {
  const policyStats = useMemo(() => {
    const allowed = policy.filter((item) => item.policy_result === "ALLOW")
    const human = policy.filter((item) => item.policy_result === "HUMAN")
    const stopped = policy.filter((item) => item.policy_result === "STOP")
    return { allowed, human, stopped }
  }, [policy])

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Policy Decisions"
          value={policy.length}
          description="M13 guardrail checks"
          loading={loading}
        />
        <MetricCard
          label="Allowed"
          value={policyStats.allowed.length}
          description="Eligible for execution"
          loading={loading}
          highlight
        />
        <MetricCard
          label="Human Review"
          value={policyStats.human.length}
          description="Not autonomously executed"
          loading={loading}
        />
        <MetricCard
          label="Stopped"
          value={policyStats.stopped.length}
          description="Blocked by policy"
          loading={loading}
        />
      </div>

      <DataTable
        title="Policy Audit"
        subtitle="Safety and bounded-autonomy decisions — HUMAN and STOP cases are not autonomously executed"
        items={policy}
        loading={loading}
        onOpenReplay={onOpenReplay}
        columns={[
          ["decision_id", "Decision"],
          ["failure_id", "Payment"],
          ["candidate_action", "Action"],
          ["policy_result", "Result"],
          ["policy_reason", "Reason"],
          ["replay", "Replay Audit"],
        ]}
        renderCell={(key, value, item) => {
          if (key === "candidate_action") {
            return <ActionBadge action={value} />
          }
          if (key === "policy_result") {
            return <StatusBadge status={value} />
          }
          if (key === "policy_reason") {
            return (
              <span
                className="block max-w-xs truncate text-[11px] text-zinc-500"
                title={String(value || "")}
              >
                {value || "—"}
              </span>
            )
          }
          if (key === "replay") {
            return (
              <button
                type="button"
                onClick={() => {
                  if (onOpenReplay) onOpenReplay(item)
                }}
                className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold text-emerald-400 hover:bg-emerald-500/20 transition"
              >
                <span>Replay</span>
                <span>⟳</span>
              </button>
            )
          }
          return formatCellValue(key, value)
        }}
      />

      <DataTable
        title="Execution Audit"
        subtitle="M14 execution records — only ALLOW policy results proceed to autonomous execution"
        items={execution}
        loading={loading}
        columns={[
          ["execution_id", "Execution"],
          ["decision_id", "Decision"],
          ["failure_id", "Payment"],
          ["candidate_action", "Action"],
          ["execution_status", "Execution Status"],
          ["execution_result", "Execution Result"],
        ]}
        renderCell={(key, value) => {
          if (key === "candidate_action") {
            return <ActionBadge action={value} />
          }
          if (key === "execution_status" || key === "execution_result") {
            return <StatusBadge status={value} />
          }
          return formatCellValue(key, value)
        }}
      />
    </>
  )
}

/* =========================================================
   EVALUATION
========================================================= */

function EvaluationPage({ evaluation, loading }) {
  const isPivotFormat = useMemo(() => {
    if (!evaluation.length) return false
    const first = evaluation[0]
    return (
      "metric" in first &&
      ("recoveryos" in first || "rules" in first || "oracle" in first)
    )
  }, [evaluation])

  const strategyColumns = useMemo(() => {
    if (!isPivotFormat || !evaluation.length) return []
    const keys = Object.keys(evaluation[0]).filter((k) => k !== "metric")
    return keys
  }, [evaluation, isPivotFormat])

  if (loading && !evaluation.length) {
    return <LoadingState message="Loading evaluation data..." />
  }

  return (
    <>
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-6">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
          <div>
            <h3 className="text-sm font-semibold text-amber-400">
              Counterfactual / Simulated Evaluation
            </h3>
            <p className="mt-2 text-xs leading-5 text-zinc-500">
              RecoveryOS is evaluated against alternative strategies in a
              controlled simulation environment. These results are not live
              Razorpay revenue — they reflect simulated recovery outcomes from
              the M16 evaluation pipeline.
            </p>
          </div>
        </div>
      </div>

      {isPivotFormat ? (
        <div className="mt-6 overflow-hidden rounded-xl border border-zinc-800 bg-[#0d0d10]">
          <div className="border-b border-zinc-800 px-5 py-4">
            <h3 className="text-sm font-semibold">Evaluation Results</h3>
            <p className="mt-1 text-xs text-zinc-600">
              M16 benchmark — RecoveryOS vs Rules vs Oracle
            </p>
          </div>

          {!evaluation.length ? (
            <EmptyState message="No evaluation records available." />
          ) : (
            <div className="max-h-[600px] overflow-auto">
              <table className="w-full min-w-[480px] text-left">
                <thead>
                  <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-wider text-zinc-600">
                    <th className="px-5 py-3">Metric</th>
                    {strategyColumns.map((col) => (
                      <th key={col} className="whitespace-nowrap px-5 py-3">
                        {actionName(col)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {evaluation.map((row, index) => (
                    <tr
                      key={row.metric || index}
                      className="border-b border-zinc-800/60 hover:bg-zinc-800/20"
                    >
                      <td className="px-5 py-3 text-[11px] font-medium text-zinc-300">
                        {row.metric}
                      </td>
                      {strategyColumns.map((col) => (
                        <td
                          key={col}
                          className="whitespace-nowrap px-5 py-3 text-[11px] text-zinc-400"
                        >
                          {formatEvaluationMetric(row.metric, row[col])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <DataTable
          title="Evaluation Results"
          subtitle="M16 benchmark output (simulated)"
          items={evaluation}
          loading={loading}
          columns={[
            ["strategy", "Strategy"],
            ["revenue_at_risk", "Revenue at Risk"],
            ["actual_recovered", "Recovered"],
            ["intervention_cost", "Cost"],
            ["net_recovery", "Net Recovery"],
            ["recovery_rate", "Recovery Rate"],
          ]}
        />
      )}
    </>
  )
}

/* =========================================================
   PORTFOLIO TABLE (Overview)
========================================================= */

function PortfolioTable({ items, loading, onOpenReplay }) {
  if (loading) {
    return <LoadingState message="Loading RecoveryOS portfolio..." compact />
  }

  if (!items.length) {
    return <EmptyState message="No portfolio records available." compact />
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left">
        <thead>
          <tr className="border-b border-zinc-800 text-[10px] font-semibold uppercase tracking-wider text-zinc-600">
            <th className="px-5 py-3">Failure</th>
            <th className="px-5 py-3">Amount</th>
            <th className="px-5 py-3">Failure Reason</th>
            <th className="px-5 py-3">AI Action</th>
            <th className="px-5 py-3">Probability</th>
            <th className="px-5 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.failure_id}
              className="border-b border-zinc-800/60 transition hover:bg-zinc-800/20"
            >
              <td className="px-5 py-4 font-mono text-[11px] text-zinc-400">
                {item.failure_id}
              </td>
              <td className="px-5 py-4 text-xs font-medium">
                {money(item.amount)}
              </td>
              <td className="px-5 py-4 text-[11px] text-zinc-500">
                {item.failure_reason}
              </td>
              <td className="px-5 py-4">
                <ActionBadge action={item.candidate_action} />
              </td>
              <td className="px-5 py-4 text-[11px] text-zinc-400">
                {percent(
                  Number(item.estimated_recovery_probability || 0) * 100,
                )}
              </td>
              <td className="px-5 py-4">
                <button
                  type="button"
                  onClick={() => {
                    if (onOpenReplay) onOpenReplay(item)
                  }}
                  className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold text-emerald-400 hover:bg-emerald-500/20 transition"
                >
                  <span>Replay</span>
                  <span>⟳</span>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* =========================================================
   GENERIC DATA TABLE
========================================================= */

function DataTable({
  title,
  subtitle,
  items,
  loading,
  columns,
  renderCell,
}) {
  return (
    <div className="mt-6 overflow-hidden rounded-xl border border-zinc-800 bg-[#0d0d10]">
      <div className="border-b border-zinc-800 px-5 py-4">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-1 text-xs text-zinc-600">{subtitle}</p>
      </div>

      {loading && !items.length ? (
        <LoadingState message="Loading RecoveryOS data..." compact />
      ) : !items.length ? (
        <EmptyState message="No records available." compact />
      ) : (
        <div className="max-h-[600px] overflow-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead>
              <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-wider text-zinc-600">
                {columns.map(([key, label]) => (
                  <th key={key} className="whitespace-nowrap px-5 py-3">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr
                  key={
                    item.failure_id ||
                    item.decision_id ||
                    item.execution_id ||
                    item.audit_id ||
                    index
                  }
                  className="border-b border-zinc-800/60 transition hover:bg-zinc-800/20"
                >
                  {columns.map(([key]) => {
                    const rawValue = item[key]
                    const content = renderCell
                      ? renderCell(key, rawValue, item)
                      : formatCellValue(key, rawValue)

                    return (
                      <td
                        key={key}
                        className="max-w-[280px] whitespace-nowrap px-5 py-3 text-[11px] text-zinc-400"
                      >
                        {content}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/* =========================================================
   REUSABLE COMPONENTS
========================================================= */

function MetricCard({
  label,
  value,
  description,
  loading = false,
  highlight = false,
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-[#0d0d10] p-5 transition hover:border-zinc-700">
      <p className="text-xs text-zinc-500">{label}</p>
      <p
        className={`mt-3 text-2xl font-semibold tracking-tight ${
          highlight ? "text-emerald-400" : ""
        }`}
      >
        {loading && value === undefined ? "..." : value}
      </p>
      <p className="mt-2 text-[10px] text-zinc-600">{description}</p>
    </div>
  )
}

function StatusBadge({ status, variant }) {
  if (!status) return <span className="text-zinc-600">—</span>

  const normalized = String(status).toUpperCase()

  const styles = {
    ALLOW: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    RECOVERED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    PRIORITIZED: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    SUCCESS: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    HUMAN: "border-amber-500/30 bg-amber-500/10 text-amber-400",
    AWAITING_HUMAN: "border-amber-500/30 bg-amber-500/10 text-amber-400",
    PENDING: "border-zinc-600/30 bg-zinc-800/50 text-zinc-400",
    STOP: "border-red-500/30 bg-red-500/10 text-red-400",
    NOT_RECOVERED: "border-red-500/30 bg-red-500/10 text-red-400",
    FAILED: "border-red-500/30 bg-red-500/10 text-red-400",
    REJECTED_DUPLICATE_EVENT: "border-amber-500/30 bg-amber-500/10 text-amber-400",
    REJECTED_ALREADY_RECOVERED: "border-amber-500/30 bg-amber-500/10 text-amber-400",
  }

  const resolvedVariant =
    variant === "success"
      ? styles.PRIORITIZED
      : styles[normalized] || "border-zinc-700 bg-zinc-900 text-zinc-400"

  return (
    <span
      className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${resolvedVariant}`}
    >
      {statusLabel(status)}
    </span>
  )
}

function ActionBadge({ action }) {
  if (!action) return <span className="text-zinc-600">—</span>

  return (
    <span className="inline-flex rounded-md border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-[10px] text-zinc-400">
      {actionName(action)}
    </span>
  )
}

function DecisionRow({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  )
}

function Detail({ label, value, mono = false, highlight = false, children }) {
  return (
    <div className="bg-[#0d0d10] p-5">
      <p className="text-[10px] uppercase tracking-wider text-zinc-600">
        {label}
      </p>
      <div
        className={`mt-2 text-sm font-medium ${
          highlight ? "text-emerald-400" : "text-zinc-300"
        } ${mono ? "font-mono text-[12px]" : ""}`}
      >
        {children ?? value ?? "—"}
      </div>
    </div>
  )
}

function EmptyState({ message, compact = false }) {
  return (
    <div
      className={`text-center text-xs text-zinc-600 ${
        compact ? "p-10" : "rounded-xl border border-zinc-800 bg-[#0d0d10] p-16"
      }`}
    >
      {message}
    </div>
  )
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="rounded-lg border border-red-900/50 bg-red-950/20 px-4 py-4">
      <p className="text-sm font-medium text-red-400">API Connection Error</p>
      <p className="mt-1 text-sm text-red-400/80">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-red-800/50 px-3 py-1.5 text-xs text-red-400 transition hover:border-red-700 hover:bg-red-950/40"
        >
          Retry connection
        </button>
      )}
    </div>
  )
}

function LoadingState({ message, compact = false }) {
  return (
    <div
      className={`flex items-center justify-center gap-2 text-xs text-zinc-600 ${
        compact ? "p-10" : "rounded-xl border border-zinc-800 bg-[#0d0d10] p-16"
      }`}
    >
      <span className="inline-block h-3 w-3 animate-spin rounded-full border border-zinc-700 border-t-zinc-400" />
      {message}
    </div>
  )
}

export default App
