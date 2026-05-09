"""
Production-ready Analytics Agent Service
Processes and analyzes civic data for insights and reporting
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import json
from collections import defaultdict

from app.shared.firestore.client import get_firestore_client
from app.shared.gemini.client import get_gemini_client
from app.shared.logging.logger import get_logger
from app.shared.retry.retry_engine import with_retry, DEFAULT_RETRY
from app.shared.schemas.monitoring import AnalyticsReport, TrendAnalysis, WardMetrics

logger = get_logger(__name__)


class AnalyticsAgentService:
    """Production-ready analytics agent service"""
    
    def __init__(self):
        self.firestore = None
        self.gemini = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize analytics agent dependencies"""
        self.firestore = await get_firestore_client()
        self.gemini = await get_gemini_client()
        self._initialized = True
        logger.info("AnalyticsAgentService initialized")
    
    @with_retry(DEFAULT_RETRY)
    async def generate_daily_analytics(self, target_date: Optional[datetime] = None) -> AnalyticsReport:
        """
        Generate comprehensive daily analytics report
        
        Args:
            target_date: Date for analytics (defaults to yesterday)
            
        Returns:
            Complete analytics report
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            if not target_date:
                target_date = datetime.utcnow() - timedelta(days=1)
            
            logger.info(f"Generating daily analytics for {target_date.date()}")
            
            start_time = datetime.utcnow()
            
            # Set date ranges
            date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            # Gather data from all sources
            complaint_data = await self._gather_complaint_analytics(date_start, date_end)
            housing_data = await self._gather_housing_analytics(date_start, date_end)
            whatsapp_data = await self._gather_whatsapp_analytics(date_start, date_end)
            ward_data = await self._gather_ward_analytics(date_start, date_end)
            
            # Process trend analysis
            trend_analysis = await self._analyze_trends(date_start, date_end)
            
            # Generate insights using AI
            insights = await self._generate_insights(
                complaint_data, housing_data, whatsapp_data, ward_data
            )
            
            # Calculate KPIs
            kpis = self._calculate_kpis(complaint_data, housing_data, whatsapp_data)
            
            # Create comprehensive report
            report = AnalyticsReport(
                report_date=target_date.date(),
                generated_at=datetime.utcnow(),
                complaint_analytics=complaint_data,
                housing_analytics=housing_data,
                whatsapp_analytics=whatsapp_data,
                ward_analytics=ward_data,
                trend_analysis=trend_analysis,
                insights=insights,
                kpis=kpis,
                processing_time_seconds=(datetime.utcnow() - start_time).total_seconds()
            )
            
            # Save report to Firestore
            await self._save_analytics_report(report)
            
            # Generate summary for stakeholders
            await self._generate_stakeholder_summary(report)
            
            logger.info(
                "Daily analytics generated",
                date=target_date.date(),
                total_complaints=complaint_data.get('total_complaints', 0),
                processing_time=report.processing_time_seconds
            )
            
            return report
            
        except Exception as e:
            logger.error(
                "Daily analytics generation failed",
                target_date=target_date,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def _gather_complaint_analytics(
        self,
        date_start: datetime,
        date_end: datetime
    ) -> Dict[str, Any]:
        """Gather complaint-related analytics"""
        try:
            # Get complaints for the date range
            complaints_query = self.firestore.collection('complaints').where(
                'created_at', '>=', date_start.isoformat()
            ).where('created_at', '<', date_end.isoformat()).get()
            
            complaints = [doc.to_dict() for doc in complaints_query.docs]
            
            # Basic metrics
            total_complaints = len(complaints)
            
            if total_complaints == 0:
                return {
                    'total_complaints': 0,
                    'by_category': {},
                    'by_severity': {},
                    'by_status': {},
                    'by_ward': {},
                    'avg_resolution_time': 0.0,
                    'resolution_rate': 0.0,
                    'escalation_rate': 0.0
                }
            
            # Category breakdown
            by_category = defaultdict(int)
            by_severity = defaultdict(int)
            by_status = defaultdict(int)
            by_ward = defaultdict(int)
            
            resolution_times = []
            resolved_count = 0
            escalated_count = 0
            
            for complaint in complaints:
                # Category
                category = complaint.get('category', 'other')
                by_category[category] += 1
                
                # Severity
                severity = complaint.get('severity', 'medium')
                by_severity[severity] += 1
                
                # Status
                status = complaint.get('status', 'pending')
                by_status[status] += 1
                
                # Ward
                ward_id = complaint.get('location', {}).get('ward_id', 'unknown')
                by_ward[ward_id] += 1
                
                # Resolution time
                if status == 'resolved':
                    resolved_count += 1
                    created_at = datetime.fromisoformat(complaint['created_at'].replace('Z', '+00:00'))
                    resolved_at = datetime.fromisoformat(complaint.get('resolved_at', '').replace('Z', '+00:00'))
                    if resolved_at > created_at:
                        resolution_hours = (resolved_at - created_at).total_seconds() / 3600
                        resolution_times.append(resolution_hours)
                
                # Escalations
                if complaint.get('escalated', False):
                    escalated_count += 1
            
            # Calculate averages
            avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0
            resolution_rate = (resolved_count / total_complaints) * 100 if total_complaints > 0 else 0.0
            escalation_rate = (escalated_count / total_complaints) * 100 if total_complaints > 0 else 0.0
            
            return {
                'total_complaints': total_complaints,
                'by_category': dict(by_category),
                'by_severity': dict(by_severity),
                'by_status': dict(by_status),
                'by_ward': dict(by_ward),
                'avg_resolution_time': round(avg_resolution_time, 2),
                'resolution_rate': round(resolution_rate, 2),
                'escalation_rate': round(escalation_rate, 2),
                'resolved_count': resolved_count,
                'escalated_count': escalated_count
            }
            
        except Exception as e:
            logger.error(f"Complaint analytics gathering failed: {e}")
            return {}
    
    async def _gather_housing_analytics(
        self,
        date_start: datetime,
        date_end: datetime
    ) -> Dict[str, Any]:
        """Gather housing-related analytics"""
        try:
            # Get housing applications
            applications_query = self.firestore.collection('housing_applications').where(
                'created_at', '>=', date_start.isoformat()
            ).where('created_at', '<', date_end.isoformat()).get()
            
            applications = [doc.to_dict() for doc in applications_query.docs]
            
            # Get housing matches
            matches_query = self.firestore.collection('housing_match_logs').where(
                'matched_at', '>=', date_start.isoformat()
            ).where('matched_at', '<', date_end.isoformat()).get()
            
            matches = [doc.to_dict() for doc in matches_query.docs]
            
            total_applications = len(applications)
            total_matches = len(matches)
            
            if total_applications == 0 and total_matches == 0:
                return {
                    'total_applications': 0,
                    'total_matches': 0,
                    'by_category': {},
                    'by_status': {},
                    'avg_match_score': 0.0,
                    'conversion_rate': 0.0
                }
            
            # Application analytics
            by_category = defaultdict(int)
            by_status = defaultdict(int)
            match_scores = []
            
            for application in applications:
                category = application.get('category', 'unknown')
                by_category[category] += 1
                
                status = application.get('status', 'pending')
                by_status[status] += 1
            
            # Match analytics
            for match in matches:
                score = match.get('top_score', 0.0)
                match_scores.append(score)
            
            avg_match_score = sum(match_scores) / len(match_scores) if match_scores else 0.0
            
            # Conversion rate (matches that lead to applications)
            conversion_rate = 0.0
            if total_matches > 0:
                # This is a simplified calculation
                conversion_rate = (total_applications / total_matches) * 100
            
            return {
                'total_applications': total_applications,
                'total_matches': total_matches,
                'by_category': dict(by_category),
                'by_status': dict(by_status),
                'avg_match_score': round(avg_match_score, 2),
                'conversion_rate': round(conversion_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Housing analytics gathering failed: {e}")
            return {}
    
    async def _gather_whatsapp_analytics(
        self,
        date_start: datetime,
        date_end: datetime
    ) -> Dict[str, Any]:
        """Gather WhatsApp interaction analytics"""
        try:
            # Get WhatsApp events
            events_query = self.firestore.collection('whatsapp_events').where(
                'timestamp', '>=', date_start.isoformat()
            ).where('timestamp', '<', date_end.isoformat()).get()
            
            events = [doc.to_dict() for doc in events_query.docs]
            
            total_messages = len(events)
            
            if total_messages == 0:
                return {
                    'total_messages': 0,
                    'incoming_messages': 0,
                    'outgoing_messages': 0,
                    'by_intent': {},
                    'avg_confidence': 0.0,
                    'response_rate': 0.0,
                    'active_users': 0
                }
            
            # Message breakdown
            incoming_count = 0
            outgoing_count = 0
            by_intent = defaultdict(int)
            confidences = []
            unique_users = set()
            responses_sent = 0
            
            for event in events:
                # Direction
                if event.get('direction') == 'incoming':
                    incoming_count += 1
                    unique_users.add(event.get('conversation_id', 'unknown'))
                else:
                    outgoing_count += 1
                
                # Intent
                intent = event.get('intent_type', 'unknown')
                by_intent[intent] += 1
                
                # Confidence
                confidence = event.get('intent_confidence', 0.0)
                confidences.append(confidence)
                
                # Response rate
                if event.get('response_sent', False):
                    responses_sent += 1
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            response_rate = (responses_sent / incoming_count) * 100 if incoming_count > 0 else 0.0
            
            return {
                'total_messages': total_messages,
                'incoming_messages': incoming_count,
                'outgoing_messages': outgoing_count,
                'by_intent': dict(by_intent),
                'avg_confidence': round(avg_confidence, 2),
                'response_rate': round(response_rate, 2),
                'active_users': len(unique_users),
                'responses_sent': responses_sent
            }
            
        except Exception as e:
            logger.error(f"WhatsApp analytics gathering failed: {e}")
            return {}
    
    async def _gather_ward_analytics(
        self,
        date_start: datetime,
        date_end: datetime
    ) -> Dict[str, Any]:
        """Gather ward-specific analytics"""
        try:
            # Get ward analyses
            wards_query = self.firestore.collection('ward_analyses').get()
            wards = [doc.to_dict() for doc in wards_query.docs]
            
            # Get ward performance metrics
            ward_metrics = {}
            
            for ward in wards:
                ward_id = ward.get('ward_id', 'unknown')
                
                # Get complaints for this ward
                complaints_query = self.firestore.collection('complaints').where(
                    'location.ward_id', '==', ward_id
                ).where('created_at', '>=', date_start.isoformat()
                ).where('created_at', '<', date_end.isoformat()).get()
                
                ward_complaints = len(complaints_query.docs)
                
                # Calculate ward score
                scores = ward.get('scores', {})
                overall_score = scores.get('overall_score', 0.0)
                
                ward_metrics[ward_id] = WardMetrics(
                    ward_id=ward_id,
                    ward_name=ward.get('ward_name', 'Unknown'),
                    complaint_count=ward_complaints,
                    infrastructure_score=overall_score,
                    priority_level=ward.get('priority_analysis', {}).get('priority_level', 'medium'),
                    last_analyzed=ward.get('analyzed_at')
                )
            
            # Calculate ward rankings
            sorted_wards = sorted(
                ward_metrics.values(),
                key=lambda x: x.infrastructure_score,
                reverse=True
            )
            
            return {
                'total_wards': len(ward_metrics),
                'ward_metrics': {ward_id: metrics.dict() for ward_id, metrics in ward_metrics.items()},
                'top_performing_wards': [ward.dict() for ward in sorted_wards[:5]],
                'needs_attention_wards': [ward.dict() for ward in sorted_wards[-5:]],
                'avg_infrastructure_score': sum(m.infrastructure_score for m in ward_metrics.values()) / len(ward_metrics) if ward_metrics else 0.0
            }
            
        except Exception as e:
            logger.error(f"Ward analytics gathering failed: {e}")
            return {}
    
    async def _analyze_trends(
        self,
        date_start: datetime,
        date_end: datetime
    ) -> TrendAnalysis:
        """Analyze trends and patterns"""
        try:
            # Get historical data for comparison
            comparison_start = date_start - timedelta(days=7)
            comparison_end = date_end - timedelta(days=7)
            
            # Current period data
            current_complaints = await self._gather_complaint_analytics(date_start, date_end)
            current_housing = await self._gather_housing_analytics(date_start, date_end)
            current_whatsapp = await self._gather_whatsapp_analytics(date_start, date_end)
            
            # Comparison period data
            previous_complaints = await self._gather_complaint_analytics(comparison_start, comparison_end)
            previous_housing = await self._gather_housing_analytics(comparison_start, comparison_end)
            previous_whatsapp = await self._gather_whatsapp_analytics(comparison_start, comparison_end)
            
            # Calculate trends
            complaint_trend = self._calculate_trend(
                previous_complaints.get('total_complaints', 0),
                current_complaints.get('total_complaints', 0)
            )
            
            housing_trend = self._calculate_trend(
                previous_housing.get('total_applications', 0),
                current_housing.get('total_applications', 0)
            )
            
            whatsapp_trend = self._calculate_trend(
                previous_whatsapp.get('total_messages', 0),
                current_whatsapp.get('total_messages', 0)
            )
            
            # Identify patterns
            patterns = await self._identify_patterns(current_complaints, current_housing, current_whatsapp)
            
            return TrendAnalysis(
                complaint_trend=complaint_trend,
                housing_trend=housing_trend,
                whatsapp_trend=whatsapp_trend,
                patterns=patterns,
                analysis_period=f"{date_start.date()} to {date_end.date()}",
                comparison_period=f"{comparison_start.date()} to {comparison_end.date()}"
            )
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return TrendAnalysis()
    
    def _calculate_trend(self, previous_value: int, current_value: int) -> Dict[str, Any]:
        """Calculate trend between two periods"""
        if previous_value == 0:
            if current_value == 0:
                return {'direction': 'stable', 'change_percent': 0.0, 'change_absolute': 0}
            else:
                return {'direction': 'increasing', 'change_percent': 100.0, 'change_absolute': current_value}
        
        change_absolute = current_value - previous_value
        change_percent = (change_absolute / previous_value) * 100
        
        if change_percent > 5:
            direction = 'increasing'
        elif change_percent < -5:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        return {
            'direction': direction,
            'change_percent': round(change_percent, 2),
            'change_absolute': change_absolute
        }
    
    async def _identify_patterns(
        self,
        complaint_data: Dict[str, Any],
        housing_data: Dict[str, Any],
        whatsapp_data: Dict[str, Any]
    ) -> List[str]:
        """Identify patterns and anomalies"""
        patterns = []
        
        # Complaint patterns
        if complaint_data.get('escalation_rate', 0) > 20:
            patterns.append("High escalation rate indicates process issues")
        
        if complaint_data.get('avg_resolution_time', 0) > 72:
            patterns.append("Slow complaint resolution times")
        
        # Housing patterns
        if housing_data.get('conversion_rate', 0) < 10:
            patterns.append("Low housing application conversion rate")
        
        # WhatsApp patterns
        if whatsapp_data.get('response_rate', 0) < 80:
            patterns.append("Low WhatsApp response rate")
        
        # Category patterns
        complaint_categories = complaint_data.get('by_category', {})
        if complaint_categories.get('water', 0) > complaint_categories.get('sanitation', 0) * 2:
            patterns.append("Water issues significantly higher than sanitation")
        
        return patterns
    
    async def _generate_insights(
        self,
        complaint_data: Dict[str, Any],
        housing_data: Dict[str, Any],
        whatsapp_data: Dict[str, Any],
        ward_data: Dict[str, Any]
    ) -> List[str]:
        """Generate AI-powered insights"""
        try:
            # Prepare data for AI analysis
            summary_data = {
                'complaints': {
                    'total': complaint_data.get('total_complaints', 0),
                    'resolution_rate': complaint_data.get('resolution_rate', 0),
                    'escalation_rate': complaint_data.get('escalation_rate', 0),
                    'top_category': max(complaint_data.get('by_category', {}).items(), key=lambda x: x[1])[0] if complaint_data.get('by_category') else 'none'
                },
                'housing': {
                    'applications': housing_data.get('total_applications', 0),
                    'matches': housing_data.get('total_matches', 0),
                    'conversion_rate': housing_data.get('conversion_rate', 0)
                },
                'whatsapp': {
                    'messages': whatsapp_data.get('total_messages', 0),
                    'response_rate': whatsapp_data.get('response_rate', 0),
                    'active_users': whatsapp_data.get('active_users', 0)
                },
                'wards': {
                    'total': ward_data.get('total_wards', 0),
                    'avg_score': ward_data.get('avg_infrastructure_score', 0)
                }
            }
            
            # Generate insights using Gemini
            prompt = f"""
            Analyze this civic services data and generate 3-5 key insights for city administrators:
            
            {json.dumps(summary_data, indent=2)}
            
            Focus on:
            1. Performance highlights or concerns
            2. Areas needing attention
            3. Positive trends to continue
            4. Operational recommendations
            5. Resource allocation suggestions
            
            Provide insights in bullet points, concise and actionable.
            """
            
            response = await self.gemini.generate_text(prompt, temperature=0.3)
            
            # Parse insights
            insights = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                    insights.append(line[1:].strip())
            
            return insights[:5]  # Limit to 5 insights
            
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return ["Unable to generate AI insights due to processing error"]
    
    def _calculate_kpis(
        self,
        complaint_data: Dict[str, Any],
        housing_data: Dict[str, Any],
        whatsapp_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate key performance indicators"""
        return {
            'service_efficiency': {
                'complaint_resolution_rate': complaint_data.get('resolution_rate', 0),
                'avg_resolution_time_hours': complaint_data.get('avg_resolution_time', 0),
                'escalation_rate': complaint_data.get('escalation_rate', 0)
            },
            'citizen_engagement': {
                'whatsapp_response_rate': whatsapp_data.get('response_rate', 0),
                'active_users': whatsapp_data.get('active_users', 0),
                'total_interactions': whatsapp_data.get('total_messages', 0)
            },
            'housing_performance': {
                'application_conversion_rate': housing_data.get('conversion_rate', 0),
                'avg_match_score': housing_data.get('avg_match_score', 0),
                'total_applications': housing_data.get('total_applications', 0)
            }
        }
    
    async def _save_analytics_report(self, report: AnalyticsReport) -> None:
        """Save analytics report to Firestore"""
        try:
            report_data = report.dict()
            
            # Use date as document ID for easy retrieval
            doc_id = report.report_date.isoformat()
            
            await self.firestore.collection('daily_analytics').document(doc_id).set(report_data)
            
        except Exception as e:
            logger.error(f"Failed to save analytics report: {e}")
            raise
    
    async def _generate_stakeholder_summary(self, report: AnalyticsReport) -> None:
        """Generate summary for different stakeholders"""
        try:
            # Executive summary
            executive_summary = f"""
            📊 Daily Analytics Summary - {report.report_date}
            
            🏢 Complaints: {report.complaint_analytics.get('total_complaints', 0)}
            ✅ Resolution Rate: {report.complaint_analytics.get('resolution_rate', 0)}%
            ⚡ WhatsApp Users: {report.whatsapp_analytics.get('active_users', 0)}
            🏠 Housing Applications: {report.housing_analytics.get('total_applications', 0)}
            """
            
            # Save summary
            await self.firestore.collection('executive_summaries').add({
                'date': report.report_date.isoformat(),
                'summary': executive_summary.strip(),
                'created_at': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to generate stakeholder summary: {e}")
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics for dashboard"""
        try:
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            
            # Get last 24 hours data
            recent_complaints = await self._gather_complaint_analytics(last_24h, now)
            recent_whatsapp = await self._gather_whatsapp_analytics(last_24h, now)
            
            # Get active conversations
            active_conversations_query = self.firestore.collection('whatsapp_conversations').where(
                'last_activity', '>=', (now - timedelta(hours=1)).isoformat()
            ).get()
            
            active_conversations = len(active_conversations_query.docs)
            
            # Get pending complaints
            pending_complaints_query = self.firestore.collection('complaints').where(
                'status', 'in', ['pending', 'classified', 'routed']
            ).get()
            
            pending_complaints = len(pending_complaints_query.docs)
            
            return {
                'last_24h': {
                    'complaints': recent_complaints.get('total_complaints', 0),
                    'whatsapp_messages': recent_whatsapp.get('total_messages', 0),
                    'resolution_rate': recent_complaints.get('resolution_rate', 0)
                },
                'real_time': {
                    'active_conversations': active_conversations,
                    'pending_complaints': pending_complaints,
                    'system_health': 'healthy'  # Would include actual health checks
                },
                'timestamp': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Real-time metrics failed: {e}")
            return {}
    
    async def generate_weekly_report(self, week_start: datetime) -> AnalyticsReport:
        """Generate comprehensive weekly report"""
        try:
            week_end = week_start + timedelta(days=7)
            
            # Aggregate daily reports
            daily_reports = []
            current_date = week_start
            
            while current_date < week_end:
                daily_report = await self.generate_daily_analytics(current_date)
                daily_reports.append(daily_report)
                current_date += timedelta(days=1)
            
            # Create weekly summary
            weekly_summary = self._aggregate_weekly_data(daily_reports)
            
            return weekly_summary
            
        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
            raise
    
    def _aggregate_weekly_data(self, daily_reports: List[AnalyticsReport]) -> AnalyticsReport:
        """Aggregate daily reports into weekly summary"""
        # This would aggregate all daily data into weekly metrics
        # For now, return the last daily report as placeholder
        return daily_reports[-1] if daily_reports else AnalyticsReport()


# Global service instance
_analytics_agent: Optional[AnalyticsAgentService] = None


async def get_analytics_agent() -> AnalyticsAgentService:
    """Get or create analytics agent service"""
    global _analytics_agent
    
    if not _analytics_agent:
        _analytics_agent = AnalyticsAgentService()
        await _analytics_agent.initialize()
    
    return _analytics_agent


async def initialize_analytics_agent():
    """Initialize analytics agent service"""
    await get_analytics_agent()
