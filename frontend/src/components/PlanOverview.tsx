import { ChartLineUp, DownloadSimple } from "@phosphor-icons/react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Plan, Scenario, money, number, totals } from "@/lib/energy";

export function PlanOverview({
  plan,
  scenario,
  onExport,
}: {
  plan: Plan;
  scenario: Scenario;
  onExport: () => void;
}) {
  const metrics = totals(plan);
  return (
    <>
      <div className="results-head">
        <div>
          <p className="section-kicker">
            LIVE PLAN / {plan.schedule.length} HOURS
          </p>
          <h2>{scenario.name}</h2>
        </div>
        <button type="button" className="outline-button" onClick={onExport}>
          <DownloadSimple size={17} /> Export JSON
        </button>
      </div>
      <div className="metric-grid">
        <Metric
          label="Estimated cost"
          value={money(metrics.cost)}
          accent="green"
        />
        <Metric label="Grid energy" value={`${number(metrics.grid)} kWh`} />
        <Metric
          label="Peak grid draw"
          value={`${number(metrics.peak)} kW`}
          accent="amber"
        />
        <Metric
          label="Solar used"
          value={`${number(metrics.solar)} kWh`}
          accent="blue"
        />
      </div>
      <div className="chart-panel panel">
        <div className="chart-title">
          <div>
            <p className="section-kicker">ENERGY FLOW</p>
            <h3>Demand vs. available supply</h3>
          </div>
          <div className="legend">
            <span className="legend-demand" /> Demand{" "}
            <span className="legend-solar" /> Solar{" "}
            <span className="legend-grid" /> Grid
          </div>
        </div>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={plan.schedule}
              margin={{ top: 8, right: 8, left: -20, bottom: 0 }}
            >
              <CartesianGrid vertical={false} stroke="#e4e8e4" />
              <XAxis
                dataKey="hour"
                tickFormatter={(hour) => `${hour}h`}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#84908a", fontSize: 11 }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#84908a", fontSize: 11 }}
              />
              <Tooltip
                cursor={{ fill: "#f2f5f1" }}
                formatter={(value) => [`${Number(value).toFixed(1)} kWh`, ""]}
              />
              <Bar
                dataKey="demand_kwh"
                fill="#243b35"
                radius={[3, 3, 0, 0]}
                barSize={9}
              />
              <Bar
                dataKey="solar_kwh"
                fill="#b6d86a"
                radius={[3, 3, 0, 0]}
                barSize={9}
              />
              <Bar
                dataKey="grid_kwh"
                fill="#f0b45b"
                radius={[3, 3, 0, 0]}
                barSize={9}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="lower-grid">
        <div className="panel directives">
          <div className="chart-title">
            <div>
              <p className="section-kicker">INTERPRETATION</p>
              <h3>Operator directives</h3>
            </div>
            <span className="count-badge">
              {plan.interpretations.length} notes
            </span>
          </div>
          {plan.interpretations.map((item, index) => (
            <div className="directive" key={index}>
              <div className="directive-number">0{index + 1}</div>
              <div>
                <strong>{item.directive}</strong>
                <p>{item.explanation}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="panel summary-panel">
          <p className="section-kicker">PLAN SUMMARY</p>
          <h3>What changed</h3>
          <p className="summary-copy">{plan.summary}</p>
          <div className="summary-line">
            <span>Solar contribution</span>
            <strong>
              {number(
                (metrics.solar / Math.max(metrics.solar + metrics.grid, 1)) *
                  100,
              )}
              %
            </strong>
          </div>
          <div className="summary-line">
            <span>Battery end state</span>
            <strong>
              {number(plan.schedule.at(-1)?.battery_energy_kwh ?? 0)} kWh
            </strong>
          </div>
        </div>
      </div>
    </>
  );
}

function Metric({
  label,
  value,
  accent = "",
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className={`metric ${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>
        <ChartLineUp size={13} /> plan estimate
      </small>
    </div>
  );
}
