"""Extract structured data from parsed documents."""

from __future__ import annotations

import re
from typing import Any

from app.document_parser.schemas import (
    AadhaarData,
    IncomeCertificateData,
    RationCardData,
)
from app.document_parser.validator import (
    clean_text,
    extract_numbers,
    normalize_name,
    parse_income_amount,
    validate_aadhaar_number,
)
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class ExtractionError(Exception):
    """Raised when extraction fails."""


class DocumentExtractor:
    """Extract structured data from parsed documents."""

    def extract_aadhaar(self, parsed_data: dict) -> AadhaarData:
        """Extract Aadhaar card data."""
        text = parsed_data.get("text", "")
        form_fields = parsed_data.get("form_fields", {})
        
        # Extract name
        name = self._extract_name(text, form_fields)
        
        # Extract Aadhaar number
        aadhaar_number = self._extract_aadhaar_number(text, form_fields)
        
        # Extract address
        address = self._extract_address(text, form_fields)
        
        # Extract DOB
        dob = self._extract_dob(text, form_fields)
        
        # Extract gender
        gender = self._extract_gender(text, form_fields)
        
        logger.info(
            "aadhaar_extracted",
            name=name,
            aadhaar_masked=f"XXXX-XXXX-{aadhaar_number[-4:]}",
        )
        
        return AadhaarData(
            fullName=name,
            aadhaarNumber=aadhaar_number,
            address=address,
            dateOfBirth=dob,
            gender=gender,
        )

    def extract_income_certificate(self, parsed_data: dict) -> IncomeCertificateData:
        """Extract income certificate data."""
        text = parsed_data.get("text", "")
        form_fields = parsed_data.get("form_fields", {})
        
        # Extract name
        name = self._extract_name(text, form_fields)
        
        # Extract annual income
        annual_income = self._extract_income(text, form_fields)
        
        # Extract issuing authority
        issuing_authority = self._extract_issuing_authority(text, form_fields)
        
        # Extract certificate number
        cert_number = self._extract_certificate_number(text, form_fields)
        
        logger.info(
            "income_certificate_extracted",
            name=name,
            income=annual_income,
            authority=issuing_authority,
        )
        
        return IncomeCertificateData(
            citizenName=name,
            annualIncome=annual_income,
            issuingAuthority=issuing_authority,
            certificateNumber=cert_number,
        )

    def extract_ration_card(self, parsed_data: dict) -> RationCardData:
        """Extract ration card data."""
        text = parsed_data.get("text", "")
        form_fields = parsed_data.get("form_fields", {})
        
        # Extract family head
        family_head = self._extract_name(text, form_fields)
        
        # Extract family count
        family_count = self._extract_family_count(text, form_fields)
        
        # Extract address
        address = self._extract_address(text, form_fields)
        
        # Extract ration card type
        card_type = self._extract_ration_type(text, form_fields)
        
        # Extract member names
        member_names = self._extract_member_names(text, form_fields)
        
        logger.info(
            "ration_card_extracted",
            family_head=family_head,
            family_count=family_count,
            card_type=card_type,
        )
        
        return RationCardData(
            familyHead=family_head,
            familyCount=family_count,
            address=address,
            rationCardType=card_type,
            memberNames=member_names,
        )

    def _extract_name(self, text: str, form_fields: dict) -> str:
        """Extract person name."""
        # Try form fields first
        for key in ["Name", "name", "Full Name", "Citizen Name", "Applicant Name"]:
            if key in form_fields:
                name = normalize_name(form_fields[key])
                if len(name) >= 2:
                    return name
        
        # Try pattern matching in text
        name_patterns = [
            r"Name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:Full Name|Citizen Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = normalize_name(match.group(1))
                if len(name) >= 2:
                    return name
        
        raise ExtractionError("Could not extract name from document")

    def _extract_aadhaar_number(self, text: str, form_fields: dict) -> str:
        """Extract Aadhaar number."""
        # Try form fields
        for key in ["Aadhaar", "Aadhaar Number", "UID", "Enrollment No"]:
            if key in form_fields:
                aadhaar = extract_numbers(form_fields[key])
                if validate_aadhaar_number(aadhaar):
                    return aadhaar
        
        # Try pattern matching - 12 digit number
        pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"
        matches = re.findall(pattern, text)
        
        for match in matches:
            aadhaar = extract_numbers(match)
            if validate_aadhaar_number(aadhaar):
                return aadhaar
        
        raise ExtractionError("Could not extract valid Aadhaar number")

    def _extract_address(self, text: str, form_fields: dict) -> str:
        """Extract address."""
        # Try form fields
        for key in ["Address", "address", "Permanent Address", "Residential Address"]:
            if key in form_fields:
                address = clean_text(form_fields[key])
                if len(address) >= 5:
                    return address
        
        # Try pattern matching
        address_pattern = r"Address[:\s]+(.+?)(?:\n|$)"
        match = re.search(address_pattern, text, re.IGNORECASE)
        if match:
            address = clean_text(match.group(1))
            if len(address) >= 5:
                return address
        
        return "Address not found"

    def _extract_dob(self, text: str, form_fields: dict) -> Optional[str]:
        """Extract date of birth."""
        # Try form fields
        for key in ["DOB", "Date of Birth", "Birth Date"]:
            if key in form_fields:
                return clean_text(form_fields[key])
        
        # Try pattern matching - DD/MM/YYYY or DD-MM-YYYY
        dob_pattern = r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
        match = re.search(dob_pattern, text)
        if match:
            return match.group(0)
        
        return None

    def _extract_gender(self, text: str, form_fields: dict) -> Optional[str]:
        """Extract gender."""
        # Try form fields
        for key in ["Gender", "gender", "Sex"]:
            if key in form_fields:
                gender = form_fields[key].strip().upper()
                if gender in ["MALE", "FEMALE", "M", "F"]:
                    return "Male" if gender in ["MALE", "M"] else "Female"
        
        # Try pattern matching
        if re.search(r"\b(MALE|Male)\b", text):
            return "Male"
        if re.search(r"\b(FEMALE|Female)\b", text):
            return "Female"
        
        return None

    def _extract_income(self, text: str, form_fields: dict) -> int:
        """Extract annual income."""
        # Try form fields
        for key in ["Annual Income", "Income", "Total Income", "Yearly Income"]:
            if key in form_fields:
                try:
                    return parse_income_amount(form_fields[key])
                except:
                    pass
        
        # Try pattern matching
        income_patterns = [
            r"Annual Income[:\s]+Rs\.?\s?(\d+(?:,\d+)*)",
            r"Income[:\s]+Rs\.?\s?(\d+(?:,\d+)*)",
            r"Rs\.?\s?(\d+(?:,\d+)*)\s+per\s+annum",
        ]
        
        for pattern in income_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return parse_income_amount(match.group(1))
                except:
                    pass
        
        raise ExtractionError("Could not extract income from document")

    def _extract_issuing_authority(self, text: str, form_fields: dict) -> str:
        """Extract issuing authority."""
        # Try form fields
        for key in ["Issuing Authority", "Authority", "Issued By"]:
            if key in form_fields:
                authority = clean_text(form_fields[key])
                if len(authority) >= 2:
                    return authority
        
        # Try pattern matching
        authority_patterns = [
            r"Issued by[:\s]+(.+?)(?:\n|$)",
            r"Authority[:\s]+(.+?)(?:\n|$)",
        ]
        
        for pattern in authority_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                authority = clean_text(match.group(1))
                if len(authority) >= 2:
                    return authority
        
        return "Government Authority"

    def _extract_certificate_number(self, text: str, form_fields: dict) -> Optional[str]:
        """Extract certificate number."""
        # Try form fields
        for key in ["Certificate Number", "Cert No", "Number"]:
            if key in form_fields:
                return clean_text(form_fields[key])
        
        # Try pattern matching
        cert_pattern = r"Certificate No[.:\s]+([A-Z0-9/-]+)"
        match = re.search(cert_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None

    def _extract_family_count(self, text: str, form_fields: dict) -> int:
        """Extract family member count."""
        # Try form fields
        for key in ["Family Members", "Total Members", "Members", "Family Size"]:
            if key in form_fields:
                try:
                    count = int(extract_numbers(form_fields[key]))
                    if 1 <= count <= 20:
                        return count
                except:
                    pass
        
        # Try pattern matching
        count_patterns = [
            r"Total Members[:\s]+(\d+)",
            r"Family Members[:\s]+(\d+)",
            r"Members[:\s]+(\d+)",
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    count = int(match.group(1))
                    if 1 <= count <= 20:
                        return count
                except:
                    pass
        
        # Default to 1 if not found
        return 1

    def _extract_ration_type(self, text: str, form_fields: dict) -> Optional[str]:
        """Extract ration card type."""
        # Try form fields
        for key in ["Card Type", "Type", "Category"]:
            if key in form_fields:
                return clean_text(form_fields[key])
        
        # Try pattern matching
        types = ["APL", "BPL", "AAY", "PHH"]
        for card_type in types:
            if card_type in text.upper():
                return card_type
        
        return None

    def _extract_member_names(self, text: str, form_fields: dict) -> list[str]:
        """Extract family member names."""
        members = []
        
        # Try form fields
        for key, value in form_fields.items():
            if "member" in key.lower() or "name" in key.lower():
                name = normalize_name(value)
                if len(name) >= 2 and name not in members:
                    members.append(name)
        
        return members[:10]  # Limit to 10 members
