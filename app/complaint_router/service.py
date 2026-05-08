"""
Production-ready Complaint Router Service
Routes classified complaints to appropriate officers and departments
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

from app.complaint_classifier.department_mapper import get_department_mapper
from app.complaint_classifier.severity_engine import get_severity_engine
from app.shared.firestore.client import get_firestore_client
from app.shared.logging.logger import get_logger
from app.shared.pubsub.publisher import publish_notification_event, publish_routing_event
from app.shared.retry.retry_engine import with_retry, DEFAULT_RETRY
from app.shared.schemas.complaint import ComplaintStatus, ComplaintSeverity

logger = get_logger(__name__)


class ComplaintRouterService:
    """Production-ready complaint routing service"""
    
    def __init__(self):
        self.department_mapper = None
        self.severity_engine = None
        self.firestore = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize routing service dependencies"""
        self.department_mapper = get_department_mapper()
        self.severity_engine = get_severity_engine()
        self.firestore = await get_firestore_client()
        self._initialized = True
        logger.info("ComplaintRouterService initialized")
    
    @with_retry(DEFAULT_RETRY)
    async def route_complaint(
        self,
        complaint_id: str,
        classification: Dict[str, Any],
        complaint_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route a classified complaint to the appropriate officer
        
        Args:
            complaint_id: Complaint ID
            classification: AI classification result
            complaint_data: Original complaint data
            
        Returns:
            Routing result with officer assignment
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            logger.info(
                "Starting complaint routing",
                complaint_id=complaint_id,
                category=classification.get('category'),
                severity=classification.get('severity')
            )
            
            # Extract routing information
            category = classification.get('category')
            severity = classification.get('severity')
            confidence = classification.get('confidence', 0.0)
            location = complaint_data.get('location', {})
            ward_id = location.get('ward_id')
            
            # Get department for category
            department = self.department_mapper.get_department_for_category(
                category, ward_id, severity
            )
            
            # Get appropriate officer
            officer = await self._assign_officer(
                department, ward_id, severity, confidence
            )
            
            if not officer:
                raise Exception(f"No officer available for department {department}")
            
            # Calculate routing priority
            priority = self._calculate_routing_priority(
                severity, confidence, location
            )
            
            # Estimate resolution time
            resolution_time = self.department_mapper.get_resolution_time_estimate(
                department, severity, ward_id
            )
            
            # Create routing record
            routing_record = {
                'complaint_id': complaint_id,
                'department': department.value,
                'officer_id': officer['id'],
                'officer_name': officer['name'],
                'ward_id': ward_id,
                'priority': priority,
                'severity': severity,
                'category': category,
                'confidence': confidence,
                'estimated_resolution_hours': resolution_time['estimated_hours'],
                'routed_at': datetime.utcnow().isoformat(),
                'routing_method': 'auto_ai',
                'status': 'assigned'
            }
            
            # Save routing to Firestore
            await self._save_routing_record(routing_record)
            
            # Update complaint with routing info
            await self._update_complaint_routing(complaint_id, routing_record)
            
            # Send notifications
            await self._send_routing_notifications(routing_record, complaint_data)
            
            # Publish routing event
            await self._publish_routing_event(routing_record, complaint_data)
            
            # Update officer workload
            await self._update_officer_workload(officer['id'])
            
            logger.info(
                "Complaint routed successfully",
                complaint_id=complaint_id,
                department=department.value,
                officer_id=officer['id'],
                priority=priority
            )
            
            return {
                'success': True,
                'routing': routing_record,
                'officer': officer,
                'resolution_estimate': resolution_time,
                'next_action': 'officer_notification'
            }
            
        except Exception as e:
            logger.error(
                "Complaint routing failed",
                complaint_id=complaint_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Mark routing as failed
            await self._mark_routing_failed(complaint_id, str(e))
            raise
    
    async def _assign_officer(
        self,
        department: str,
        ward_id: Optional[str],
        severity: str,
        confidence: float
    ) -> Optional[Dict[str, Any]]:
        """Assign the best available officer"""
        try:
            # Convert string to enum
            from app.shared.schemas.complaint import Department
            dept_enum = Department(department)
            
            # Get priority score
            priority = self._calculate_routing_priority(severity, confidence)
            
            # Find available officer
            officer = self.department_mapper.get_officer_for_department(
                dept_enum, ward_id, priority
            )
            
            if not officer:
                # Try to find any officer in the department
                officer = self.department_mapper.get_officer_for_department(
                    dept_enum, None, priority
                )
            
            if officer and not officer.get('available', True):
                # Find backup officer
                officer = await self._find_backup_officer(dept_enum, ward_id, priority)
            
            return officer
            
        except Exception as e:
            logger.error(f"Officer assignment failed: {e}")
            return None
    
    async def _find_backup_officer(
        self,
        department,
        ward_id: Optional[str],
        priority: int
    ) -> Optional[Dict[str, Any]]:
        """Find backup officer when primary is unavailable"""
        try:
            # Query Firestore for backup officers
            query = self.firestore.collection('officers').where(
                'department', '==', department.value
            ).where('available', '==', True)
            
            if ward_id:
                query = query.where('ward_id', '==', ward_id)
            
            docs = await query.get()
            
            # Find officer with lowest workload
            best_officer = None
            min_workload = float('inf')
            
            for doc in docs:
                officer_data = doc.to_dict()
                workload = officer_data.get('current_load', 0)
                
                if workload < min_workload and workload < officer_data.get('max_load', 20):
                    min_workload = workload
                    best_officer = {
                        'id': doc.id,
                        **officer_data
                    }
            
            return best_officer
            
        except Exception as e:
            logger.error(f"Backup officer search failed: {e}")
            return None
    
    def _calculate_routing_priority(
        self,
        severity: str,
        confidence: float,
        location: Optional[Dict[str, Any]] = None
    ) -> int:
        """Calculate routing priority (1-10, higher = more urgent)"""
        base_priority = 5
        
        # Severity-based priority
        severity_priority = {
            'critical': 4,
            'high': 3,
            'medium': 1,
            'low': 0
        }
        
        priority = base_priority + severity_priority.get(severity, 0)
        
        # Confidence boost
        if confidence > 0.9:
            priority += 1
        
        # Location-based adjustments
        if location:
            if location.get('is_slum_area', False):
                priority += 1
            if location.get('near_sensitive_location', False):
                priority += 1
        
        return min(priority, 10)
    
    async def _save_routing_record(self, routing_record: Dict[str, Any]) -> None:
        """Save routing record to Firestore"""
        try:
            await self.firestore.collection('complaint_routing').add(routing_record)
        except Exception as e:
            logger.error(f"Failed to save routing record: {e}")
            raise
    
    async def _update_complaint_routing(
        self,
        complaint_id: str,
        routing_record: Dict[str, Any]
    ) -> None:
        """Update complaint with routing information"""
        try:
            update_data = {
                'routing': routing_record,
                'status': ComplaintStatus.ROUTED.value,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            await self.firestore.collection('complaints').document(complaint_id).update(update_data)
        except Exception as e:
            logger.error(f"Failed to update complaint routing: {e}")
            raise
    
    async def _send_routing_notifications(
        self,
        routing_record: Dict[str, Any],
        complaint_data: Dict[str, Any]
    ) -> None:
        """Send notifications to assigned officer"""
        try:
            officer_id = routing_record['officer_id']
            complaint_id = routing_record['complaint_id']
            
            # Get officer details
            officer_doc = await self.firestore.collection('officers').document(officer_id).get()
            if not officer_doc.exists:
                logger.warning(f"Officer {officer_id} not found for notification")
                return
            
            officer = officer_doc.to_dict()
            
            # Prepare notification message
            message = self._generate_officer_notification_message(routing_record, complaint_data)
            
            # Send push notification
            await publish_notification_event(
                notification_type='complaint_assigned',
                recipient_id=officer_id,
                message=message,
                data={
                    'complaint_id': complaint_id,
                    'priority': routing_record['priority'],
                    'category': routing_record['category'],
                    'severity': routing_record['severity'],
                    'action_required': 'review_and_acknowledge'
                }
            )
            
            # Send WhatsApp notification if officer has phone
            if officer.get('phone_number'):
                await self._send_whatsapp_notification(officer, message, routing_record)
            
            logger.info(
                "Notifications sent to officer",
                officer_id=officer_id,
                complaint_id=complaint_id
            )
            
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")
            # Don't raise - routing succeeded, just notification failed
    
    def _generate_officer_notification_message(
        self,
        routing_record: Dict[str, Any],
        complaint_data: Dict[str, Any]
    ) -> str:
        """Generate notification message for officer"""
        priority_emoji = {
            10: '🚨', 9: '🔴', 8: '🟠', 7: '🟡',
            6: '🟢', 5: '🔵', 4: '⚪', 3: '⚫',
            2: '🔘', 1: '⭕'
        }
        
        emoji = priority_emoji.get(routing_record['priority'], '📋')
        
        message = f"""
{emoji} New Complaint Assigned

Category: {routing_record['category'].title()}
Severity: {routing_record['severity'].title()}
Priority: {routing_record['priority']}/10
Location: Ward {routing_record.get('ward_id', 'Unknown')}

Description: {complaint_data.get('description', 'No description')[:100]}...

Estimated Resolution: {routing_record['estimated_resolution_hours']} hours

Action Required: Please review and acknowledge
"""
        
        return message.strip()
    
    async def _send_whatsapp_notification(
        self,
        officer: Dict[str, Any],
        message: str,
        routing_record: Dict[str, Any]
    ) -> None:
        """Send WhatsApp notification to officer"""
        try:
            # This would integrate with WhatsApp service
            # For now, just log the notification
            logger.info(
                "WhatsApp notification would be sent",
                officer_phone=officer.get('phone_number'),
                complaint_id=routing_record['complaint_id']
            )
        except Exception as e:
            logger.error(f"WhatsApp notification failed: {e}")
    
    async def _publish_routing_event(
        self,
        routing_record: Dict[str, Any],
        complaint_data: Dict[str, Any]
    ) -> None:
        """Publish routing event for other services"""
        try:
            await publish_routing_event(
                complaint_id=routing_record['complaint_id'],
                officer_id=routing_record['officer_id'],
                department=routing_record['department'],
                routing_data={
                    'priority': routing_record['priority'],
                    'estimated_resolution_hours': routing_record['estimated_resolution_hours'],
                    'routed_at': routing_record['routed_at']
                }
            )
        except Exception as e:
            logger.error(f"Failed to publish routing event: {e}")
    
    async def _update_officer_workload(self, officer_id: str) -> None:
        """Update officer's current workload"""
        try:
            await self.firestore.collection('officers').document(officer_id).update({
                'current_load': firestore.Increment(1),
                'last_assigned': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to update officer workload: {e}")
    
    async def _mark_routing_failed(self, complaint_id: str, error: str) -> None:
        """Mark routing as failed"""
        try:
            await self.firestore.collection('complaints').document(complaint_id).update({
                'status': ComplaintStatus.PENDING.value,
                'routing_error': error,
                'routing_failed_at': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to mark routing failure: {e}")
    
    async def escalate_complaint(
        self,
        complaint_id: str,
        reason: str,
        escalated_by: str
    ) -> Dict[str, Any]:
        """
        Escalate complaint to higher authority
        
        Args:
            complaint_id: Complaint to escalate
            reason: Reason for escalation
            escalated_by: Who is escalating
            
        Returns:
            Escalation result
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get current routing
            routing_doc = await self.firestore.collection('complaint_routing').where(
                'complaint_id', '==', complaint_id
            ).get()
            
            if not routing_doc.docs:
                raise Exception("No routing record found for complaint")
            
            current_routing = routing_doc.docs[0].to_dict()
            current_department = current_routing['department']
            
            # Get escalation path
            from app.shared.schemas.complaint import ComplaintCategory
            category = ComplaintCategory(current_routing['category'])
            escalation_path = self.department_mapper.get_escalation_path(category)
            
            # Find current department index
            try:
                from app.shared.schemas.complaint import Department
                current_dept_enum = Department(current_department)
                current_index = escalation_path.index(current_dept_enum)
            except ValueError:
                current_index = -1
            
            # Escalate to next level
            if current_index + 1 < len(escalation_path):
                next_department = escalation_path[current_index + 1]
                
                # Assign to higher authority
                new_officer = await self._assign_officer(
                    next_department.value,
                    current_routing.get('ward_id'),
                    'critical',  # Escalated complaints get high priority
                    1.0
                )
                
                if not new_officer:
                    raise Exception("No officer available for escalation")
                
                # Create escalation record
                escalation_record = {
                    'complaint_id': complaint_id,
                    'from_department': current_department,
                    'to_department': next_department.value,
                    'from_officer_id': current_routing['officer_id'],
                    'to_officer_id': new_officer['id'],
                    'reason': reason,
                    'escalated_by': escalated_by,
                    'escalated_at': datetime.utcnow().isoformat(),
                    'status': 'escalated'
                }
                
                # Save escalation
                await self.firestore.collection('complaint_escalations').add(escalation_record)
                
                # Update routing
                new_routing = current_routing.copy()
                new_routing.update({
                    'department': next_department.value,
                    'officer_id': new_officer['id'],
                    'officer_name': new_officer['name'],
                    'priority': 10,  # Maximum priority for escalated
                    'escalated': True,
                    'escalated_at': datetime.utcnow().isoformat()
                })
                
                await self.firestore.collection('complaint_routing').document(
                    routing_doc.docs[0].id
                ).update(new_routing)
                
                # Update complaint
                await self.firestore.collection('complaints').document(complaint_id).update({
                    'status': ComplaintStatus.ESCALATED.value,
                    'escalation': escalation_record,
                    'updated_at': datetime.utcnow().isoformat()
                })
                
                # Send notifications
                await self._send_escalation_notifications(escalation_record, new_officer)
                
                logger.info(
                    "Complaint escalated successfully",
                    complaint_id=complaint_id,
                    from_dept=current_department,
                    to_dept=next_department.value
                )
                
                return {
                    'success': True,
                    'escalation': escalation_record,
                    'new_officer': new_officer,
                    'new_routing': new_routing
                }
            else:
                raise Exception("No higher department available for escalation")
                
        except Exception as e:
            logger.error(
                "Complaint escalation failed",
                complaint_id=complaint_id,
                error=str(e)
            )
            raise
    
    async def _send_escalation_notifications(
        self,
        escalation_record: Dict[str, Any],
        new_officer: Dict[str, Any]
    ) -> None:
        """Send escalation notifications"""
        try:
            message = f"""
🚨 COMPLAINT ESCALATED

Complaint ID: {escalation_record['complaint_id']}
From: {escalation_record['from_department'].title()}
To: {escalation_record['to_department'].title()}
Reason: {escalation_record['reason']}

Please review and take immediate action.
"""
            
            await publish_notification_event(
                notification_type='complaint_escalated',
                recipient_id=new_officer['id'],
                message=message.strip(),
                data={
                    'complaint_id': escalation_record['complaint_id'],
                    'escalation_reason': escalation_record['reason'],
                    'action_required': 'immediate_review'
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send escalation notifications: {e}")
    
    async def get_routing_statistics(
        self,
        department: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get routing statistics for monitoring"""
        try:
            query = self.firestore.collection('complaint_routing')
            
            if department:
                query = query.where('department', '==', department)
            if date_from:
                query = query.where('routed_at', '>=', date_from.isoformat())
            if date_to:
                query = query.where('routed_at', '<=', date_to.isoformat())
            
            docs = await query.get()
            
            stats = {
                'total_routed': len(docs),
                'by_department': {},
                'by_priority': {},
                'by_severity': {},
                'avg_resolution_estimate': 0.0,
                'escalations': 0
            }
            
            total_resolution_time = 0.0
            
            for doc in docs:
                data = doc.to_dict()
                
                # Department stats
                dept = data.get('department', 'unknown')
                stats['by_department'][dept] = stats['by_department'].get(dept, 0) + 1
                
                # Priority stats
                priority = data.get('priority', 5)
                priority_bucket = f"{priority}-{priority+1}"
                stats['by_priority'][priority_bucket] = stats['by_priority'].get(priority_bucket, 0) + 1
                
                # Severity stats
                severity = data.get('severity', 'medium')
                stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
                
                # Resolution time
                resolution_time = data.get('estimated_resolution_hours', 0)
                total_resolution_time += resolution_time
                
                # Escalations
                if data.get('escalated', False):
                    stats['escalations'] += 1
            
            if stats['total_routed'] > 0:
                stats['avg_resolution_estimate'] = total_resolution_time / stats['total_routed']
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get routing statistics: {e}")
            raise


# Global service instance
_router_service: Optional[ComplaintRouterService] = None


async def get_complaint_router() -> ComplaintRouterService:
    """Get or create complaint router service"""
    global _router_service
    
    if not _router_service:
        _router_service = ComplaintRouterService()
        await _router_service.initialize()
    
    return _router_service


async def initialize_complaint_router():
    """Initialize complaint router service"""
    await get_complaint_router()
