import type { ScenarioId, DecisionResponse, ShapContribution } from "./api/types";

export const SCENARIO_NAMES: Record<ScenarioId, string> = {
  chemical: "化工",
  metallurgy: "冶金",
  dust: "粉尘",
};

export const SCENARIO_LABELS: Record<ScenarioId, string> = SCENARIO_NAMES;

export const SCENARIO_CONFIG: Record<string, unknown> = {
  chemical: {
    confidence_threshold: 0.6,
    risk_threshold: 0.5,
    checker_strictness: "medium",
    memory_top_k: 5,
  },
  metallurgy: {
    confidence_threshold: 0.65,
    risk_threshold: 0.55,
    checker_strictness: "high",
    memory_top_k: 5,
  },
  dust: {
    confidence_threshold: 0.5,
    risk_threshold: 0.45,
    checker_strictness: "low",
    memory_top_k: 3,
  },
};

function baseDemoRecord(scenario: ScenarioId) {
  switch (scenario) {
    case "chemical":
      return {
        temperature_c: 78.5,
        pressure_pa: 101325,
        flow_rate: 12.3,
        level_pct: 67,
      };
    case "metallurgy":
      return {
        furnace_temp_c: 1450,
        feed_rate: 3.2,
        oxygen_pct: 21,
      };
    case "dust":
      return {
        dust_density_mg_m3: 15.2,
        humidity_pct: 12,
        conveyor_load: 0.82,
      };
  }
}

export function getDemoDataJson(scenario: ScenarioId): string {
  const rec = baseDemoRecord(scenario);
  return JSON.stringify({ enterprise_id: "ENT-DEMO-001", ...rec }, null, 2);
}

function randomProbabilities(levels = ["红", "橙", "黄", "蓝"]) {
  const vals = levels.map(() => Math.random());
  const sum = vals.reduce((a, b) => a + b, 0) || 1;
  const normalized: Record<string, number> = {};
  levels.forEach((l, i) => (normalized[l] = Math.round((vals[i] / sum) * 100) / 100));
  return normalized;
}

export function generateMockDecision(scenario: ScenarioId, enterpriseId = "ENT-DEMO-001"): DecisionResponse {
  const probs = randomProbabilities();
  const maxLevel = Object.entries(probs).sort((a, b) => b[1] - a[1])[0][0];
  const shap: ShapContribution[] = [
    { feature: "主要因子A", contribution: 0.4 },
    { feature: "主要因子B", contribution: 0.2 },
  ];
  return {
    enterprise_id: enterpriseId,
    scenario_id: scenario,
    final_status: "ok",
    predicted_level: maxLevel,
    probability_distribution: probs,
    shap_contributions: shap,
    mock: true,
    node_status: [
      { node: "feature_extraction", status: "done", timestamp: Date.now(), mock: true },
      { node: "model_inference", status: "done", timestamp: Date.now(), mock: true },
    ],
  } as DecisionResponse;
}
