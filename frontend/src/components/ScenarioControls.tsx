import {
  BatteryChargingIcon,
  CaretRightIcon,
  Play,
  PlayIcon,
} from "@phosphor-icons/react";
import { Battery, Scenario, sampleScenario } from "@/lib/energy";

type ScenarioControlsProps = {
  scenario: Scenario;
  isRunning: boolean;
  message: string;
  onScenarioChange: (scenario: Scenario) => void;
  onHourChange: (
    index: number,
    field: "demand_kwh" | "solar_kwh" | "tariff_bdt_per_kwh",
    value: string,
  ) => void;
  onBatteryChange: (field: keyof Battery, value: string) => void;
  onLoad: (scenario: Scenario) => void;
  onRun: () => void;
};

const batteryFields: [keyof Battery, string][] = [
  ["capacity_kwh", "Capacity"],
  ["initial_energy_kwh", "Initial"],
  ["minimum_energy_kwh", "Reserve"],
  ["max_charge_kwh", "Max charge"],
  ["max_discharge_kwh", "Max discharge"],
];

export function ScenarioControls({
  scenario,
  isRunning,
  message,
  onScenarioChange,
  onHourChange,
  onBatteryChange,
  onLoad,
  onRun,
}: ScenarioControlsProps) {
  return (
    <aside className="control-panel panel">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">SCENARIO INPUT</p>
          <h2>Set the conditions</h2>
        </div>
        <button
          type="button"
          className="text-button"
          onClick={() => onLoad(sampleScenario())}
        >
          Reset
        </button>
      </div>
      <label className="label">
        Scenario name
        <input
          className="input"
          value={scenario.name}
          onChange={(e) =>
            onScenarioChange({ ...scenario, name: e.target.value })
          }
        />
      </label>
      <div className="preset-row">
        <button
          type="button"
          className={`preset ${scenario.name === "Campus weekday" ? "active" : ""}`}
          onClick={() => onLoad(sampleScenario())}
        >
          Campus weekday
        </button>
        <button
          type="button"
          className={`preset ${scenario.name === "Cloudy campus day" ? "active" : ""}`}
          onClick={() => onLoad(sampleScenario("cloudy"))}
        >
          Cloudy day
        </button>
      </div>
      <div className="subheading">
        <BatteryChargingIcon size={18} /> Battery configuration
      </div>
      <div className="battery-grid">
        {batteryFields.map(([field, label]) => (
          <label className="label" key={field}>
            {label}
            <div className="unit-input">
              <input
                type="number"
                min="0"
                step="1"
                value={scenario.battery[field]}
                onChange={(e) => onBatteryChange(field, e.target.value)}
              />
              <span>kWh</span>
            </div>
          </label>
        ))}
      </div>
      <div className="subheading notes-heading">
        <span className="note-icon">✦</span> Operator notes
      </div>
      {scenario.notes.map((note, index) => (
        <textarea
          className="note-input"
          aria-label={`Operator note ${index + 1}`}
          key={index}
          value={note}
          onChange={(e) =>
            onScenarioChange({
              ...scenario,
              notes: scenario.notes.map((current, i) =>
                i === index ? e.target.value : current,
              ),
            })
          }
        />
      ))}
      <details className="hours-editor">
        <summary>Hourly demand, solar &amp; tariff</summary>
        <div className="hours-scroll">
          <div className="hours-head">
            <span>Hour</span>
            <span>Demand</span>
            <span>Solar</span>
            <span>Tariff</span>
          </div>
          {scenario.hours.map((hour, index) => (
            <div className="hour-input-row" key={hour.hour}>
              <strong>{String(hour.hour).padStart(2, "0")}:00</strong>
              <input
                aria-label={`Demand at ${hour.hour}:00`}
                type="number"
                min="0"
                step="0.1"
                value={hour.demand_kwh}
                onChange={(e) =>
                  onHourChange(index, "demand_kwh", e.target.value)
                }
              />
              <input
                aria-label={`Solar at ${hour.hour}:00`}
                type="number"
                min="0"
                step="0.1"
                value={hour.solar_kwh}
                onChange={(e) =>
                  onHourChange(index, "solar_kwh", e.target.value)
                }
              />
              <input
                aria-label={`Tariff at ${hour.hour}:00`}
                type="number"
                min="0"
                step="0.1"
                value={hour.tariff_bdt_per_kwh}
                onChange={(e) =>
                  onHourChange(index, "tariff_bdt_per_kwh", e.target.value)
                }
              />
            </div>
          ))}
        </div>
      </details>
      <button
        type="button"
        className="run-button"
        onClick={onRun}
        disabled={isRunning}
      >
        <PlayIcon weight="fill" size={17} />
        {isRunning ? "Finding best schedule..." : "Run optimization"}
        <CaretRightIcon size={18} />
      </button>
      {message && <p className="error-message">{message}</p>}
    </aside>
  );
}
