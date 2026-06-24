from pydantic import BaseModel


class CreateCompanySchema(BaseModel):

    company_name: str

    sector: str

    country: str

    city: str

    employees_count: int

    annual_revenue: float