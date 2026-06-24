import API from "./api";

export const subscriptionService = {
  async getSubscription() {
    const res = await API.get("/subscription");
    return res.data;
  },

  async getStatus() {
    const res = await API.get("/subscription/status");
    return res.data;
  },

  async activate() {
    const res = await API.post("/subscription/activate");
    return res.data;
  },

  async cancel() {
    const res = await API.post("/subscription/cancel");
    return res.data;
  },
};
