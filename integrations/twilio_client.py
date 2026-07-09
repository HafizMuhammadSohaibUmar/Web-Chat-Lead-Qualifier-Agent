"""Twilio owner alert client."""
import logging

import httpx

from config import get_settings
from logging_utils import log_event
from models.lead import Lead

logger = logging.getLogger("twilio")


class TwilioClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_phone_number
        self.api_base = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

    async def alert_owner(self, lead: Lead) -> bool:
        settings = get_settings()
        body = (
            f"New website chat lead: {lead.name} needs {lead.service_type}. "
            f"Urgency: {lead.urgency}. Contact: {lead.phone or lead.email}. Address: {lead.address}."
        )
        if settings.sms_dry_run:
            log_event(logger, "Owner SMS dry run", body_preview=body[:160])
            return True
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.api_base}/Messages.json",
                auth=(self.account_sid, self.auth_token),
                data={"To": settings.owner_phone_number, "From": self.from_number, "Body": body},
            )
            response.raise_for_status()
        return True


twilio_client = TwilioClient()
