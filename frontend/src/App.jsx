import { useEffect, useMemo, useRef, useState } from "react"

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

const navItems = [
  { name: "Overview", icon: "▦" },
  { name: "Portfolio", icon: "◫" },
  { name: "Decisions", icon: "◇" },
  { name: "Outcomes", icon: "↗" },
  { name: "Audit", icon: "◌" },
  { name: "Evaluation", icon: "◎" },
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
    maximumFractionDigits: 0,
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
  const [data, setData] = useState({
    overview: null,
    portfolio: [],
    decisions: [],
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
    Outcomes: "Measured recovery results from executed interventions.",
    Audit: "Policy, execution and control evidence.",
    Evaluation: "Benchmark RecoveryOS against alternative strategies.",
  }

  const navigateTo = (page) => {
    setActivePage(page)
    setMobileNavOpen(false)
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100">
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
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-bold text-black">
                R
              </div>
              <div>
                <h1 className="text-[15px] font-semibold tracking-tight">
                  RecoveryOS
                </h1>
                <p className="text-[11px] text-zinc-500">
                  Revenue Intelligence
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
                  className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                    activePage === item.name
                      ? "bg-zinc-800/80 text-white"
                      : "text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-200"
                  }`}
                >
                  <span className="w-5 text-center text-base">{item.icon}</span>
                  {item.name}
                </button>
              ))}
            </nav>

            <div className="mt-10">
              <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-600">
                Environment
              </p>
              <div className="mx-2 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-amber-400" />
                  <span className="text-xs font-medium text-zinc-300">
                    Test Mode
                  </span>
                </div>
                <p className="mt-2 text-[11px] leading-5 text-zinc-600">
                  Simulated payment environment
                </p>
              </div>
            </div>
          </div>

          <div className="border-t border-zinc-800/80 p-4">
            <div className="flex items-center gap-3 rounded-lg px-2 py-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 text-xs font-medium">
                A
              </div>
              <div>
                <p className="text-xs font-medium text-zinc-300">
                  Recovery Workspace
                </p>
                <p className="text-[10px] text-zinc-600">Demo environment</p>
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
                <span className="text-zinc-400">Revenue Recovery</span>
              </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-3">
              <button
                type="button"
                className="hidden rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 sm:inline-flex"
              >
                Documentation
              </button>

              <button
                type="button"
                onClick={loadData}
                disabled={loading}
                className="rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-400 transition hover:border-zinc-700 hover:text-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
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
                Revenue Recovery
              </p>

              <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
                    {activePage}
                  </h2>
                  <p className="mt-2 text-sm text-zinc-500">
                    {pageDescription[activePage]}
                  </p>
                </div>

                <div className="flex w-fit items-center gap-2 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  <span className="text-xs font-medium text-amber-400">
                    Simulation / Demo Environment
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
              />
            )}

            {activePage === "Portfolio" && (
              <PortfolioPage portfolio={data.portfolio} loading={loading} />
            )}

            {activePage === "Decisions" && (
              <DecisionsPage decisions={data.decisions} loading={loading} />
            )}

            {activePage === "Outcomes" && (
              <OutcomesPage outcomes={data.outcomes} loading={loading} />
            )}

            {activePage === "Audit" && (
              <AuditPage
                policy={data.policy}
                execution={data.execution}
                loading={loading}
              />
            )}

            {activePage === "Evaluation" && (
              <EvaluationPage evaluation={data.evaluation} loading={loading} />
            )}

            <div className="mt-10 flex flex-col gap-2 border-t border-zinc-900 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-[10px] text-zinc-700">
                RecoveryOS • AI Revenue Recovery
              </p>
              <p className="text-[10px] text-zinc-700">
                Simulated evaluation environment • No live payment data
              </p>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

/* =========================================================
   OVERVIEW
========================================================= */

function OverviewPage({ overview, portfolio, stoppedCount, loading }) {
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
          <PortfolioTable items={selected.slice(0, 10)} loading={loading} />
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

function PortfolioPage({ portfolio, loading }) {
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
                  <th className="px-5 py-3">Status</th>
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
                        <StatusBadge status="PRIORITIZED" variant="success" />
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
            <button
              type="button"
              onClick={() => setSelectedCase(null)}
              className="rounded-md border border-zinc-800 px-3 py-1.5 text-xs text-zinc-500 transition hover:border-zinc-700 hover:text-zinc-200"
            >
              Close
            </button>
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

function DecisionsPage({ decisions, loading }) {
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
        columns={[
          ["decision_id", "Decision"],
          ["failure_id", "Payment"],
          ["candidate_action", "Action"],
          ["estimated_recovery_probability", "Probability"],
          ["expected_gross_recovery", "Expected Gross"],
          ["expected_net_recovery", "Expected Net"],
          ["decision_status", "Status"],
          ["decision_reason", "Reason"],
        ]}
        renderCell={(key, value, item) => {
          if (key === "candidate_action") {
            return <ActionBadge action={value} />
          }
          if (key === "decision_status") {
            return <StatusBadge status={value} />
          }
          if (key === "decision_reason") {
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

function AuditPage({ policy, execution, loading }) {
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
        columns={[
          ["decision_id", "Decision"],
          ["failure_id", "Payment"],
          ["candidate_action", "Action"],
          ["policy_result", "Result"],
          ["policy_reason", "Reason"],
        ]}
        renderCell={(key, value) => {
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

function PortfolioTable({ items, loading }) {
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
            <th className="px-5 py-3">Status</th>
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
                <StatusBadge status="PRIORITIZED" variant="success" />
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
