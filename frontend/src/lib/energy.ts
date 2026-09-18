export type Hour = {
  hour: number;
  demand_kwh: number;
  solar_kwh: number;
  tariff_bdt_per_kwh: number;
};
export type Battery = {
  capacity_kwh: number;
  initial_energy_kwh: number;
  minimum_energy_kwh: number;
  max_charge_kwh: number;
  max_discharge_kwh: number;
};
export type Scenario = {
  name: string;
  hours: Hour[];
  battery: Battery;
  notes: string[];
};
export type PlanHour = Hour & {
  grid_kwh: number;
  solar_used_kwh: number;
  charge_kwh: number;
  discharge_kwh: number;
  battery_energy_kwh: number;
  cost_bdt: number;
};
export type Plan = {
  schedule: PlanHour[];
  summary: string;
  interpretations: { note: string; directive: string; explanation: string }[];
};
export const hourLabel = (hour: number) =>
  `${String(hour).padStart(2, "0")}:00`;
export const number = (value: number, digits = 1) =>
  value.toLocaleString("en-US", { maximumFractionDigits: digits });
export const money = (value: number) => `৳${number(value, 2)}`;

export function sampleScenario(kind = "campus"): Scenario {
  const demand = [
    12, 11, 10, 10, 11, 13, 17, 22, 27, 30, 32, 33, 31, 29, 28, 30, 35, 40, 44,
    42, 34, 26, 20, 15,
  ];
  const solar = [
    0, 0, 0, 0, 0, 0, 2, 6, 14, 23, 32, 39, 42, 39, 32, 23, 12, 4, 0, 0, 0, 0,
    0, 0,
  ];
  return {
    name: kind === "cloudy" ? "Cloudy campus day" : "Campus weekday",
    hours: demand.map((d, hour) => ({
      hour,
      demand_kwh: d,
      solar_kwh: solar[hour] * (kind === "cloudy" ? 0.4 : 1),
      tariff_bdt_per_kwh: hour >= 17 && hour <= 22 ? 12 : hour < 7 ? 6 : 8,
    })),
    battery: {
      capacity_kwh: 40,
      initial_energy_kwh: 12,
      minimum_energy_kwh: 4,
      max_charge_kwh: 8,
      max_discharge_kwh: 8,
    },
    notes: [
      "Keep at least 8 kWh in the battery from 18:00 to 22:00.",
      "Do not charge the battery between 17:00 and 20:00.",
    ],
  };
}

export function validateScenario(value: unknown): asserts value is Scenario {
  if (!value || typeof value !== "object")
    throw new Error("Import a JSON scenario object.");
  const s = value as Scenario;
  if (typeof s.name !== "string" || !s.name.trim())
    throw new Error("Give your scenario a name.");
  if (!Array.isArray(s.hours) || s.hours.length !== 24)
    throw new Error("Provide exactly 24 hourly records.");
  const valid = (n: unknown) =>
    typeof n === "number" && Number.isFinite(n) && n >= 0;
  const seen = new Set<number>();
  for (const h of s.hours) {
    if (
      !h ||
      !Number.isInteger(h.hour) ||
      h.hour < 0 ||
      h.hour > 23 ||
      seen.has(h.hour)
    )
      throw new Error("Each hour from 0 to 23 must appear exactly once.");
    seen.add(h.hour);
    if (![h.demand_kwh, h.solar_kwh, h.tariff_bdt_per_kwh].every(valid))
      throw new Error(
        `Hour ${h.hour}: demand, solar and tariff must be nonnegative numbers.`,
      );
  }
  const b = s.battery;
  if (
    !b ||
    ![
      b.capacity_kwh,
      b.initial_energy_kwh,
      b.minimum_energy_kwh,
      b.max_charge_kwh,
      b.max_discharge_kwh,
    ].every(valid)
  )
    throw new Error("Enter valid, nonnegative battery values.");
  if (
    b.capacity_kwh <= 0 ||
    b.minimum_energy_kwh > b.initial_energy_kwh ||
    b.initial_energy_kwh > b.capacity_kwh
  )
    throw new Error(
      "Battery energy must satisfy: minimum ≤ initial ≤ capacity, with capacity greater than zero.",
    );
  if (
    !Array.isArray(s.notes) ||
    s.notes.length < 1 ||
    s.notes.length > 3 ||
    s.notes.some((n) => typeof n !== "string" || !n.trim() || n.length > 1000)
  )
    throw new Error("Add 1–3 notes, each between 1 and 1,000 characters.");
}

// A transparent solar-first baseline, not an optimizer or an LLM simulation.
export function previewPlan(s: Scenario): Plan {
  validateScenario(s);
  return {
    schedule: [...s.hours]
      .sort((a, b) => a.hour - b.hour)
      .map((h) => {
        const solar_used_kwh = Math.min(h.demand_kwh, h.solar_kwh);
        const grid_kwh = h.demand_kwh - solar_used_kwh;
        return {
          ...h,
          solar_used_kwh,
          grid_kwh,
          charge_kwh: 0,
          discharge_kwh: 0,
          battery_energy_kwh: s.battery.initial_energy_kwh,
          cost_bdt: grid_kwh * h.tariff_bdt_per_kwh,
        };
      }),
    interpretations: s.notes.map((note) => ({
      note,
      directive: "Awaiting interpretation",
      explanation: "Operator notes are not applied in preview mode.",
    })),
    summary:
      "This preview uses available solar first and grid energy for the remaining demand. The battery stays at its initial energy. Connect the optimization API to apply operator notes and minimize cost.",
  };
}

export function totals(plan: Plan) {
  return {
    cost: plan.schedule.reduce((n, h) => n + h.cost_bdt, 0),
    grid: plan.schedule.reduce((n, h) => n + h.grid_kwh, 0),
    peak: Math.max(...plan.schedule.map((h) => h.grid_kwh)),
    solar: plan.schedule.reduce((n, h) => n + h.solar_used_kwh, 0),
  };
}

export async function optimizeScenario(scenario: Scenario): Promise<Plan> {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) return previewPlan(scenario);
  validateScenario(scenario);
  const response = await fetch(`${url.replace(/\/$/, "")}/optimize-energy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
    signal: AbortSignal.timeout(45000),
  });
  if (!response.ok) {
    if (response.status === 404)
      throw new Error(
        "The backend is reachable, but /optimize-energy is not implemented yet.",
      );
    if (response.status === 422)
      throw new Error(
        "The backend rejected this scenario. Check the inputs and API contract.",
      );
    if (response.status === 409)
      throw new Error(
        "No feasible schedule was found. Review battery limits and operator notes.",
      );
    throw new Error(
      `Optimization failed (${response.status}). Please try again.`,
    );
  }
  const data = (await response.json()) as Plan;
  if (
    !data ||
    !Array.isArray(data.schedule) ||
    data.schedule.length !== 24 ||
    typeof data.summary !== "string" ||
    !Array.isArray(data.interpretations)
  )
    throw new Error(
      "The API returned an unsupported response. Check the documented frontend contract.",
    );
  const seen = new Set<number>();
  for (const h of data.schedule) {
    if (
      !h ||
      !Number.isInteger(h.hour) ||
      h.hour < 0 ||
      h.hour > 23 ||
      seen.has(h.hour) ||
      ![
        h.demand_kwh,
        h.solar_kwh,
        h.tariff_bdt_per_kwh,
        h.grid_kwh,
        h.solar_used_kwh,
        h.charge_kwh,
        h.discharge_kwh,
        h.battery_energy_kwh,
        h.cost_bdt,
      ].every((n) => typeof n === "number" && Number.isFinite(n) && n >= 0)
    )
      throw new Error("The API returned invalid hourly data.");
    seen.add(h.hour);
  }
  if (
    data.interpretations.some(
      (i) =>
        !i ||
        typeof i.note !== "string" ||
        typeof i.directive !== "string" ||
        typeof i.explanation !== "string",
    )
  )
    throw new Error("The API returned invalid interpretation data.");
  data.schedule.sort((a, b) => a.hour - b.hour);
  return data;
}

export function downloadJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
