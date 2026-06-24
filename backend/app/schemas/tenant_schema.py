from pydantic import BaseModel


class SelectCompanySchema(BaseModel):
    company_id: str
