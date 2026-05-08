"""
Department mapping logic for complaint routing
Maps complaint categories to responsible government departments
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from app.shared.schemas.complaint import ComplaintCategory, Department
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DepartmentInfo:
    """Department information and contact details"""
    name: str
    code: str
    contact_email: str
    contact_phone: str
    escalation_level: int
    average_resolution_time_hours: float
    working_hours: str
    jurisdiction: List[str]  # Ward IDs or areas


class DepartmentMapper:
    """Maps complaint categories to appropriate government departments"""
    
    def __init__(self):
        self.category_to_department = self._load_category_mappings()
        self.department_info = self._load_department_info()
        self.escalation_matrix = self._load_escalation_matrix()
    
    def _load_category_mappings(self) -> Dict[ComplaintCategory, Department]:
        """Load category to department mappings"""
        return {
            ComplaintCategory.WATER: Department.WATER,
            ComplaintCategory.SANITATION: Department.SANITATION,
            ComplaintCategory.ROADS: Department.ROADS,
            ComplaintCategory.ELECTRICITY: Department.ELECTRICITY,
            ComplaintCategory.HOUSING: Department.HOUSING,
            ComplaintCategory.WASTE: Department.MUNICIPAL,
            ComplaintCategory.STREET_LIGHTS: Department.ELECTRICITY,
            ComplaintCategory.DRAINAGE: Department.SANITATION,
            ComplaintCategory.EVICTION: Department.HOUSING,
            ComplaintCategory.NOISE: Department.MUNICIPAL,
            ComplaintCategory.OTHER: Department.MUNICIPAL
        }
    
    def _load_department_info(self) -> Dict[Department, DepartmentInfo]:
        """Load detailed department information"""
        return {
            Department.WATER: DepartmentInfo(
                name="Water Board",
                code="WB",
                contact_email="water@nivasai.gov.in",
                contact_phone="1800-123-4567",
                escalation_level=2,
                average_resolution_time_hours=48.0,
                working_hours="9:00 AM - 6:00 PM",
                jurisdiction=["all"]
            ),
            Department.SANITATION: DepartmentInfo(
                name="Sanitation Department",
                code="SD",
                contact_email="sanitation@nivasai.gov.in",
                contact_phone="1800-123-4568",
                escalation_level=2,
                average_resolution_time_hours=24.0,
                working_hours="8:00 AM - 8:00 PM",
                jurisdiction=["all"]
            ),
            Department.ROADS: DepartmentInfo(
                name="Public Works Department",
                code="PWD",
                contact_email="pwd@nivasai.gov.in",
                contact_phone="1800-123-4569",
                escalation_level=3,
                average_resolution_time_hours=72.0,
                working_hours="9:00 AM - 6:00 PM",
                jurisdiction=["all"]
            ),
            Department.ELECTRICITY: DepartmentInfo(
                name="Electricity Board",
                code="EB",
                contact_email="electricity@nivasai.gov.in",
                contact_phone="1800-123-4570",
                escalation_level=2,
                average_resolution_time_hours=12.0,
                working_hours="24/7 Emergency",
                jurisdiction=["all"]
            ),
            Department.HOUSING: DepartmentInfo(
                name="Housing Board",
                code="HB",
                contact_email="housing@nivasai.gov.in",
                contact_phone="1800-123-4571",
                escalation_level=3,
                average_resolution_time_hours=168.0,  # 1 week
                working_hours="10:00 AM - 5:00 PM",
                jurisdiction=["all"]
            ),
            Department.MUNICIPAL: DepartmentInfo(
                name="Municipal Corporation",
                code="MC",
                contact_email="municipal@nivasai.gov.in",
                contact_phone="1800-123-4572",
                escalation_level=1,
                average_resolution_time_hours=36.0,
                working_hours="9:00 AM - 6:00 PM",
                jurisdiction=["all"]
            ),
            Department.HEALTH: DepartmentInfo(
                name="Health Department",
                code="HD",
                contact_email="health@nivasai.gov.in",
                contact_phone="1800-123-4573",
                escalation_level=2,
                average_resolution_time_hours=24.0,
                working_hours="24/7 Emergency",
                jurisdiction=["all"]
            ),
            Department.EDUCATION: DepartmentInfo(
                name="Education Department",
                code="ED",
                contact_email="education@nivasai.gov.in",
                contact_phone="1800-123-4574",
                escalation_level=3,
                average_resolution_time_hours=120.0,
                working_hours="10:00 AM - 5:00 PM",
                jurisdiction=["all"]
            ),
            Department.POLICE: DepartmentInfo(
                name="Police Department",
                code="PD",
                contact_email="police@nivasai.gov.in",
                contact_phone="100",
                escalation_level=1,
                average_resolution_time_hours=2.0,
                working_hours="24/7",
                jurisdiction=["all"]
            ),
            Department.FIRE: DepartmentInfo(
                name="Fire Department",
                code="FD",
                contact_email="fire@nivasai.gov.in",
                contact_phone="101",
                escalation_level=1,
                average_resolution_time_hours=1.0,
                working_hours="24/7",
                jurisdiction=["all"]
            )
        }
    
    def _load_escalation_matrix(self) -> Dict[str, List[Department]]:
        """Load escalation matrix for departments"""
        return {
            "water": [Department.WATER, Department.MUNICIPAL, Department.HEALTH],
            "sanitation": [Department.SANITATION, Department.MUNICIPAL, Department.HEALTH],
            "roads": [Department.ROADS, Department.MUNICIPAL, Department.POLICE],
            "electricity": [Department.ELECTRICITY, Department.MUNICIPAL, Department.FIRE],
            "housing": [Department.HOUSING, Department.MUNICIPAL, Department.POLICE],
            "waste": [Department.MUNICIPAL, Department.HEALTH, Department.SANITATION],
            "street_lights": [Department.ELECTRICITY, Department.MUNICIPAL, Department.POLICE],
            "drainage": [Department.SANITATION, Department.WATER, Department.MUNICIPAL],
            "eviction": [Department.HOUSING, Department.POLICE, Department.MUNICIPAL],
            "noise": [Department.MUNICIPAL, Department.POLICE, Department.HEALTH],
            "other": [Department.MUNICIPAL, Department.POLICE]
        }
    
    def get_department_for_category(
        self,
        category: ComplaintCategory,
        ward_id: Optional[str] = None,
        severity: Optional[str] = None
    ) -> Department:
        """
        Get the appropriate department for a complaint category
        
        Args:
            category: Complaint category
            ward_id: Ward ID for location-based routing
            severity: Complaint severity for priority routing
            
        Returns:
            Appropriate department
        """
        try:
            # Base mapping
            department = self.category_to_department.get(category, Department.MUNICIPAL)
            
            # Ward-specific overrides (if any)
            if ward_id:
                ward_override = self._get_ward_specific_department(category, ward_id)
                if ward_override:
                    department = ward_override
            
            # Severity-based overrides
            if severity == 'critical':
                department = self._get_emergency_department(category)
            
            logger.info(
                "Department mapped",
                category=category.value,
                department=department.value,
                ward_id=ward_id,
                severity=severity
            )
            
            return department
            
        except Exception as e:
            logger.error(f"Department mapping failed: {e}")
            return Department.MUNICIPAL
    
    def _get_ward_specific_department(
        self,
        category: ComplaintCategory,
        ward_id: str
    ) -> Optional[Department]:
        """Get ward-specific department override"""
        # This could be loaded from a database or configuration
        # For now, return None (no overrides)
        return None
    
    def _get_emergency_department(self, category: ComplaintCategory) -> Department:
        """Get emergency department for critical complaints"""
        emergency_mapping = {
            ComplaintCategory.ELECTRICITY: Department.FIRE,
            ComplaintCategory.WATER: Department.HEALTH,
            ComplaintCategory.SANITATION: Department.HEALTH,
            ComplaintCategory.EVICTION: Department.POLICE,
            ComplaintCategory.NOISE: Department.POLICE
        }
        
        return emergency_mapping.get(category, Department.MUNICIPAL)
    
    def get_department_info(self, department: Department) -> DepartmentInfo:
        """Get detailed information about a department"""
        return self.department_info.get(department, self.department_info[Department.MUNICIPAL])
    
    def get_escalation_path(self, category: ComplaintCategory) -> List[Department]:
        """Get escalation path for a complaint category"""
        category_key = category.value
        return self.escalation_matrix.get(category_key, [Department.MUNICIPAL, Department.POLICE])
    
    def get_officer_for_department(
        self,
        department: Department,
        ward_id: Optional[str] = None,
        priority: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Get the best officer for a department
        
        Args:
            department: Target department
            ward_id: Ward ID for location-based assignment
            priority: Priority level (1-10, higher = more urgent)
            
        Returns:
            Officer information or None
        """
        try:
            # This would typically query a database for available officers
            # For now, return a mock officer assignment
            officer = {
                "id": f"officer_{department.value}_{ward_id or 'general'}",
                "name": f"Officer {department.value.title()}",
                "department": department.value,
                "ward_id": ward_id,
                "contact": self.department_info[department].contact_phone,
                "email": self.department_info[department].contact_email,
                "priority": priority,
                "current_load": 5,  # Number of active complaints
                "max_load": 20,
                "available": True
            }
            
            logger.info(
                "Officer assigned",
                department=department.value,
                officer_id=officer["id"],
                ward_id=ward_id,
                priority=priority
            )
            
            return officer
            
        except Exception as e:
            logger.error(f"Officer assignment failed: {e}")
            return None
    
    def get_resolution_time_estimate(
        self,
        department: Department,
        severity: Optional[str] = None,
        ward_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get estimated resolution time for a complaint
        
        Args:
            department: Target department
            severity: Complaint severity
            ward_id: Ward ID (for location-based adjustments)
            
        Returns:
            Resolution time estimate
        """
        base_time = self.department_info[department].average_resolution_time_hours
        
        # Adjust based on severity
        severity_multipliers = {
            'critical': 0.5,  # Faster for critical
            'high': 0.8,
            'medium': 1.0,
            'low': 1.5  # Slower for low priority
        }
        
        multiplier = severity_multipliers.get(severity, 1.0)
        adjusted_time = base_time * multiplier
        
        # Ward-specific adjustments (could be based on historical data)
        if ward_id:
            ward_factor = self._get_ward_time_factor(ward_id)
            adjusted_time *= ward_factor
        
        return {
            "estimated_hours": round(adjusted_time, 1),
            "estimated_days": round(adjusted_time / 24, 1),
            "base_time_hours": base_time,
            "severity_multiplier": multiplier,
            "department": department.value,
            "confidence": 0.8
        }
    
    def _get_ward_time_factor(self, ward_id: str) -> float:
        """Get ward-specific time adjustment factor"""
        # This could be based on historical data
        # For now, return 1.0 (no adjustment)
        return 1.0
    
    def validate_department_assignment(
        self,
        category: ComplaintCategory,
        department: Department
    ) -> bool:
        """Validate if a department can handle a category"""
        expected_department = self.category_to_department.get(category, Department.MUNICIPAL)
        
        # Check if department is in escalation path
        escalation_path = self.get_escalation_path(category)
        
        return (department == expected_department or 
                department in escalation_path or
                department == Department.MUNICIPAL)  # Municipal can handle anything
    
    def get_department_workload(self, department: Department) -> Dict[str, Any]:
        """Get current workload statistics for a department"""
        try:
            # This would typically query real-time data
            # For now, return mock data
            return {
                "department": department.value,
                "active_complaints": 15,
                "resolved_today": 8,
                "pending_today": 12,
                "average_resolution_time": 18.5,
                "sla_compliance": 0.85,
                "officer_utilization": 0.75,
                "last_updated": "2024-01-15T10:30:00Z"
            }
        except Exception as e:
            logger.error(f"Workload query failed: {e}")
            return {}
    
    def suggest_department_transfer(
        self,
        current_department: Department,
        category: ComplaintCategory,
        reason: str
    ) -> Optional[Department]:
        """
        Suggest department transfer if needed
        
        Args:
            current_department: Currently assigned department
            category: Complaint category
            reason: Reason for transfer suggestion
            
        Returns:
            Suggested new department or None
        """
        try:
            # Check if current department is appropriate
            if not self.validate_department_assignment(category, current_department):
                # Suggest correct department
                suggested = self.category_to_department.get(category, Department.MUNICIPAL)
                logger.info(
                    "Department transfer suggested",
                    from_dept=current_department.value,
                    to_dept=suggested.value,
                    category=category.value,
                    reason=reason
                )
                return suggested
            
            return None
            
        except Exception as e:
            logger.error(f"Transfer suggestion failed: {e}")
            return None


# Global mapper instance
_department_mapper: Optional[DepartmentMapper] = None


def get_department_mapper() -> DepartmentMapper:
    """Get or create department mapper"""
    global _department_mapper
    
    if not _department_mapper:
        _department_mapper = DepartmentMapper()
    
    return _department_mapper
