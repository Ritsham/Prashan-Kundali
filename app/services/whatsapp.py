import logging

logger = logging.getLogger(__name__)

def send_whatsapp_message(phone_number: str, text: str) -> bool:
    """
    Mock utility for sending WhatsApp messages.
    In a real implementation, this would integrate with a WhatsApp API provider (e.g. Twilio, Meta Graph API).
    """
    logger.info(f"Sending WhatsApp message to {phone_number}: {text}")
    print(f"--- WHATSAPP MESSAGE ---")
    print(f"To: {phone_number}")
    print(f"Message: {text}")
    print(f"------------------------")
    return True
