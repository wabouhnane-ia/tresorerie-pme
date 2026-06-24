import API from "./api";

export const analyticsService = {
  async getSubscription() {
    const res = await API.get("/analytics/subscription");
    return res.data;
  },

  async getLatestAnalysis() {
    const res = await API.get("/analytics/latest-analysis");
    return res.data;
  },

  async trainForecastModels(horizonDays = 30) {
    const res = await API.post("/forecast/train", {
      horizon_days: horizonDays,
    });
    return res.data;
  },

  async upgradeToPremium() {
    const res = await API.post("/billing/upgrade");
    return res.data;
  },
};
