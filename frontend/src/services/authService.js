import API from "./api";

export const authService = {

  async register(email, password, firstName, lastName) {
    const res = await API.post("/auth/register", {
      email, password,
      first_name: firstName,
      last_name: lastName
    });
    return res.data;
  },

  async login(email, password) {
    const res = await API.post("/auth/login", { email, password });
    const { access_token } = res.data;
    if (typeof window !== "undefined") {
      localStorage.setItem("token", access_token);
      const me = await this.getMe();
      localStorage.setItem("user", JSON.stringify(me));
      return { ...res.data, user: me };
    }
    return res.data;
  },

  async createCompany(name, sector, city, country = "Maroc", employeesCount = 10, annualRevenue = 1000000) {
    const res = await API.post("/companies/create", {
      company_name: name,
      sector,
      city,
      country,
      employees_count: employeesCount,
      annual_revenue: annualRevenue,
    });
    // Le nouveau token contient le company_id
    if (typeof window !== "undefined" && res.data.access_token) {
      localStorage.setItem("token", res.data.access_token);
    }
    return res.data;
  },

  async selectCompany(companyId) {
    const res = await API.post("/auth/select-company", {
      company_id: companyId
    });
    if (typeof window !== "undefined" && res.data.access_token) {
      localStorage.setItem("token", res.data.access_token);
    }
    return res.data;
  },

  async getMe() {
    const res = await API.get("/auth/me");
    return res.data;
  },

  logout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
  },

  getToken() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("token");
  },

  getUser() {
    if (typeof window === "undefined") return null;
    try {
      const u = localStorage.getItem("user");
      if (!u || u === "undefined") return null;
      return JSON.parse(u);
    } catch {
      return null;
    }
  },

  isAuthenticated() {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem("token");
  }
};
