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


class VerifyEmailInput(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendCodeInput(BaseModel):
    email: EmailStr


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class ForgotPasswordInput(BaseModel):
    email: EmailStr


class ResetPasswordInput(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
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
    client_id: Optional[str] = None


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
    service: Optional[str] = Field(default=None, max_length=120)


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
    paypal_client_id: Optional[str] = None
    paypal_secret: Optional[str] = None
    paypal_mode: Optional[str] = None
    price_consulting: Optional[float] = None
    consulting_budget_usd: Optional[float] = None
    google_api_key: Optional[str] = None
    llm_provider: Optional[str] = None
    vertex_service_account_json: Optional[str] = None
    vertex_project: Optional[str] = None
    vertex_location: Optional[str] = None
    whatsapp_enabled: Optional[bool] = None
    mail_addresses: Optional[str] = None
    price_chat_usd: Optional[float] = Field(default=None, gt=0)
    chat_messages: Optional[int] = Field(default=None, gt=0)
    price_extra_usd: Optional[float] = Field(default=None, gt=0)
    extra_messages: Optional[int] = Field(default=None, gt=0)
    trial_messages: Optional[int] = Field(default=None, ge=0)
    bank_account_pen: Optional[str] = None
    bank_account_usd: Optional[str] = None
    forward_email: Optional[str] = None
    resend_webhook_secret: Optional[str] = None
    whatsapp_number: Optional[str] = None
    whatsapp_message: Optional[str] = None


class ManualPaymentInput(BaseModel):
    item_id: str
    currency: str = "PEN"


class CreateOrderInput(BaseModel):
    item_type: str = "audit"
    item_id: str
    plan: Optional[str] = None


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
