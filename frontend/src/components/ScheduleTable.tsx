import { Plan, Scenario, hourLabel, money, number } from "@/lib/energy";

export function ScheduleTable({
  plan,
  scenario,
}: {
  plan: Plan;
  scenario: Scenario;
}) {
  return (
    <div className="schedule-panel panel">
      <div className="chart-title">
        <div>
          <p className="section-kicker">HOURLY SCHEDULE</p>
          <h3>Dispatch detail</h3>
        </div>
        <span className="scroll-hint">Scroll to inspect all 24 hours</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Hour</th>
              <th>Demand</th>
              <th>Solar used</th>
              <th>Grid</th>
              <th>Battery</th>
              <th>Tariff</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {plan.schedule.map((hour) => (
              <tr key={hour.hour}>
                <td className="hour-cell">{hourLabel(hour.hour)}</td>
                <td>{number(hour.demand_kwh)} kWh</td>
                <td className="solar-cell">
                  {number(hour.solar_used_kwh)} kWh
                </td>
                <td>{number(hour.grid_kwh)} kWh</td>
                <td>
                  <span className="battery-bar">
                    <span
                      style={{
                        width: `${Math.min(100, (hour.battery_energy_kwh / scenario.battery.capacity_kwh) * 100)}%`,
                      }}
                    />
                  </span>
                  {number(hour.battery_energy_kwh)} kWh
                </td>
                <td>{money(hour.tariff_bdt_per_kwh)}</td>
                <td className="cost-cell">{money(hour.cost_bdt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
