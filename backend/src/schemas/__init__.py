from .user import Token, User, UserCreate, UserUpdate, UserEmail
from .user_audit_log import UserAuditLog, UserAuditLogCreate, UserAuditLogUpdate
from .password_reset import PasswordResetTokenCreate, PasswordResetTokenVerify, PasswordResetTokenInDB, PasswordChange
from .address import Address, AddressCreate, AddressUpdate
from .customer import (
    CustomerRegister, CustomerProfile, CustomerUpdate,
    MagicLinkRequest, MagicLinkVerify, MagicLinkToken,
)
from .marketing import (
    MarketingConnector, MarketingConnectorCreate, MarketingConnectorUpdate,
    Campaign, CampaignCreate, CampaignUpdate, CampaignSummary,
    CampaignEvent, CampaignEventCreate, CampaignEventUpdate,
    Audience, AudienceCreate, AudienceUpdate, AudienceWithMembers,
    AudienceMember, AudienceMemberCreate,
    CampaignAnalyticsData, EventAnalyticsData,
    SmartBoostRecommendation,
)

__all__ = [
    "User", "UserCreate", "UserUpdate", "UserEmail", "Token",
    "UserAuditLog", "UserAuditLogCreate", "UserAuditLogUpdate",
    "PasswordResetTokenCreate", "PasswordResetTokenVerify", "PasswordResetTokenInDB", "PasswordChange",
    "Address", "AddressCreate", "AddressUpdate",
    # Customer self-service (FP-05)
    "CustomerRegister", "CustomerProfile", "CustomerUpdate",
    "MagicLinkRequest", "MagicLinkVerify", "MagicLinkToken",
    # Marketing
    "MarketingConnector", "MarketingConnectorCreate", "MarketingConnectorUpdate",
    "Campaign", "CampaignCreate", "CampaignUpdate", "CampaignSummary",
    "CampaignEvent", "CampaignEventCreate", "CampaignEventUpdate",
    "Audience", "AudienceCreate", "AudienceUpdate", "AudienceWithMembers",
    "AudienceMember", "AudienceMemberCreate",
    "CampaignAnalyticsData", "EventAnalyticsData",
    "SmartBoostRecommendation",
]
