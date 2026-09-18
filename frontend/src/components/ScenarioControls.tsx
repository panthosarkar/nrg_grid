import { BatteryCharging, CaretRight, Play } from "@phosphor-icons/react";
import { Battery, Scenario, sampleScenario } from "@/lib/energy";

type ScenarioControlsProps = {
  scenario: Scenario;
  isRunning: boolean;
  message: string;
  onScenarioChange: (scenario: Scenario) => void;
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
          className="preset active"
          onClick={() => onLoad(sampleScenario())}
        >
          Campus weekday
        </button>
        <button
          className="preset"
          onClick={() => onLoad(sampleScenario("cloudy"))}
        >
          Cloudy day
        </button>
      </div>
      <div className="subheading">
        <BatteryCharging size={18} /> Battery configuration
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
      <button className="run-button" onClick={onRun} disabled={isRunning}>
        <Play weight="fill" size={17} />
        {isRunning ? "Finding best schedule..." : "Run optimization"}
        <CaretRight size={18} />
      </button>
      {message && <p className="error-message">{message}</p>}
    </aside>
  );
}
