import API from "./api";

export const decisionService = {
  async getDecisions(status) {
    const params = status ? { status } : {};
    const res = await API.get("/decisions", { params });
    return res.data;
  },

  async getHistory(limit = 50) {
    const res = await API.get("/decisions/history", { params: { limit } });
    return res.data;
  },

  async getImpact() {
    const res = await API.get("/decisions/impact");
    return res.data;
  },

  async createDecision(payload) {
    const res = await API.post("/decisions", payload);
    return res.data;
  },

  async updateStatus(decisionId, status) {
    const res = await API.patch(`/decisions/${decisionId}/status`, { status });
    return res.data;
  },

  async recomputeImpact() {
    const res = await API.post("/decisions/recompute-impact");
    return res.data;
  },
};
