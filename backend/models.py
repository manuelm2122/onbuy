from typing import List, Optional, Annotated

from pydantic import BaseModel, Field, ConfigDict, BeforeValidator, EmailStr

PyObjectId = Annotated[str, BeforeValidator(str)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    def to_mongo(self) -> dict:
        d = self.model_dump(by_alias=True, exclude_none=True)
        d.pop("_id", None)
        return d

    @classmethod
    def from_mongo(cls, doc):
        return cls.model_validate(doc) if doc else None


class UserPublic(BaseDocument):
    email: str
    name: str
    role: str = "cliente"
    created_at: str


class RegisterInput(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
    accepted_terms: bool = False


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class Audit(BaseDocument):
    user_id: str
    condominium_name: str
    address: Optional[str] = None
    district: Optional[str] = None
    period: str
    purpose: Optional[str] = None
    notes: Optional[str] = None
    status: str = "pendiente"
    payment_status: str = "pendiente_pago"
    authorized_at: Optional[str] = None
    analysis: Optional[str] = None
    analysis_date: Optional[str] = None
    missing_documents: List[str] = Field(default_factory=list)
    created_at: str
    document_count: int = 0


class AuditCreate(BaseModel):
    condominium_name: str = Field(min_length=2)
    address: Optional[str] = None
    district: Optional[str] = None
    period: str = Field(min_length=2)
    purpose: Optional[str] = None
    notes: Optional[str] = None


class DocumentOut(BaseDocument):
    audit_id: str
    filename: str
    category: str
    mime_type: str
    size: int
    created_at: str


class ContactInput(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    phone: Optional[str] = None
    message: str = Field(min_length=5)


class ContactReadInput(BaseModel):
    read: bool = True


class SettingsInput(BaseModel):
    ai_model: Optional[str] = None
    price_small: Optional[float] = None
    price_medium: Optional[float] = None
    contact_email: Optional[str] = None
    empresa_razon_social: Optional[str] = None
    empresa_ruc: Optional[str] = None
    empresa_representante: Optional[str] = None
    empresa_dni: Optional[str] = None
    empresa_direccion: Optional[str] = None
    empresa_ciudad: Optional[str] = None
    llm_key: Optional[str] = None
    resend_api_key: Optional[str] = None
    resend_sender: Optional[str] = None
    complaints_notify_email: Optional[str] = None


class ComplaintInput(BaseModel):
    consumer_name: str = Field(min_length=3)
    doc_type: str
    doc_number: str = Field(min_length=6, max_length=15)
    address: str = Field(min_length=5)
    phone: str = Field(min_length=6, max_length=15)
    email: EmailStr
    item_type: str
    amount: Optional[float] = None
    service_description: str = Field(min_length=5)
    request_type: str
    detail: str = Field(min_length=10)
    consumer_request: str = Field(min_length=5)
    accepted_declaration: bool = False


class ComplaintStatusInput(BaseModel):
    status: str
    response_note: Optional[str] = None


class AdminDocInput(BaseModel):
    doc_type: str
    fields: dict = Field(default_factory=dict)
