"use client";

import { useRef, useState } from "react";
import {
  Battery,
  Plan,
  Scenario,
  downloadJson,
  optimizeScenario,
  previewPlan,
  sampleScenario,
  validateScenario,
} from "@/lib/energy";
import { AppHeader } from "./AppHeader";
import { HeroSection } from "./HeroSection";
import { PlanOverview } from "./PlanOverview";
import { ScenarioControls } from "./ScenarioControls";
import { ScheduleTable } from "./ScheduleTable";

export default function HomePage() {
  const [scenario, setScenario] = useState<Scenario>(() => sampleScenario());
  const [plan, setPlan] = useState<Plan>(() => previewPlan(sampleScenario()));
  const [isRunning, setIsRunning] = useState(false);
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  function loadScenario(next: Scenario) {
    try {
      validateScenario(next);
      setScenario(next);
      setPlan(previewPlan(next));
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Invalid scenario.");
    }
  }

  function updateBattery(field: keyof Battery, value: string) {
    const next = Number(value);
    setScenario((current) => ({
      ...current,
      battery: {
        ...current.battery,
        [field]: Number.isFinite(next) ? next : 0,
      },
    }));
  }

  function updateHour(
    index: number,
    field: "demand_kwh" | "solar_kwh" | "tariff_bdt_per_kwh",
    value: string,
  ) {
    const next = Number(value);
    setScenario((current) => ({
      ...current,
      hours: current.hours.map((hour, hourIndex) =>
        hourIndex === index
          ? { ...hour, [field]: Number.isFinite(next) ? next : 0 }
          : hour,
      ),
    }));
  }

  async function runOptimization() {
    setIsRunning(true);
    setMessage("");
    try {
      validateScenario(scenario);
      setPlan(await optimizeScenario(scenario));
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to process this scenario.",
      );
    } finally {
      setIsRunning(false);
    }
  }

  function importScenario(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        loadScenario(JSON.parse(String(reader.result)) as Scenario);
      } catch {
        setMessage("That file is not valid JSON.");
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  }

  return (
    <main className="app-shell">
      <AppHeader fileInputRef={fileInputRef} onImport={importScenario} />
      <HeroSection />
      <section className="workspace-grid">
        <ScenarioControls
          scenario={scenario}
          isRunning={isRunning}
          message={message}
          onScenarioChange={setScenario}
          onHourChange={updateHour}
          onBatteryChange={updateBattery}
          onLoad={loadScenario}
          onRun={runOptimization}
        />
        <div className="results-column">
          <PlanOverview
            plan={plan}
            scenario={scenario}
            onExport={() =>
              downloadJson(
                scenario,
                `${scenario.name.toLowerCase().replaceAll(" ", "-")}.json`,
              )
            }
          />
          <ScheduleTable plan={plan} scenario={scenario} />
        </div>
      </section>
      <footer>
        <span>NRG_Grid</span>
        <span>Deterministic preview · {new Date().getFullYear()}</span>
        <span>Optimizing for clarity, cost, and control</span>
      </footer>
    </main>
  );
}
