"""AI-powered ward intelligence brief generation."""

from __future__ import annotations

import os

import google.generativeai as genai

from app.analytics_aggregator.schemas import ComplaintMetrics, WardBrief, WardMetrics
from app.config import settings
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class BriefGenerator:
    """Generate natural language ward intelligence briefs."""

    def __init__(self):
        """Initialize brief generator."""
        self.model = None
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-1.5-pro")
            logger.info("brief_generator_initialized")
        except Exception as exc:
            logger.warning("brief_generator_init_failed", error=str(exc))

    def generate_ward_brief(
        self,
        ward_id: str,
        ward_metrics: WardMetrics,
        complaint_metrics: ComplaintMetrics,
    ) -> WardBrief:
        """
        Generate AI-powered ward intelligence brief.
        
        Args:
            ward_id: Ward identifier
            ward_metrics: Ward infrastructure metrics
            complaint_metrics: Complaint metrics
        
        Returns:
            WardBrief with AI-generated analysis
        """
        if not self.model:
            return self._generate_fallback_brief(ward_id, ward_metrics, complaint_metrics)
        
        try:
            # Build prompt
            prompt = self._build_brief_prompt(ward_id, ward_metrics, complaint_metrics)
            
            # Generate brief
            response = self.model.generate_content(prompt)
            
            # Parse response
            brief_text = response.text
            
            # Extract structured data from response
            brief = self._parse_brief_response(ward_id, brief_text, ward_metrics, complaint_metrics)
            
            logger.info("ward_brief_generated", ward_id=ward_id)
            
            return brief
        
        except Exception as exc:
            logger.error("brief_generation_failed", ward_id=ward_id, error=str(exc))
            return self._generate_fallback_brief(ward_id, ward_metrics, complaint_metrics)

    def _build_brief_prompt(
        self,
        ward_id: str,
        ward_metrics: WardMetrics,
        complaint_metrics: ComplaintMetrics,
    ) -> str:
        """Build prompt for brief generation."""
        prompt = f"""Generate a concise municipal intelligence brief for Ward {ward_id}.

Infrastructure Metrics:
- Road Quality: {ward_metrics.roadQualityScore}/100
- Sanitation: {ward_metrics.sanitationScore}/100
- Flood Risk: {ward_metrics.floodRiskScore}/100
- Green Coverage: {ward_metrics.greenCoverageScore}/100
- Overall Score: {ward_metrics.overallInfrastructureScore}/100

Complaint Metrics (Last 24 hours):
- Total Complaints: {complaint_metrics.totalComplaints}
- Resolution Rate: {complaint_metrics.resolutionRate}%
- Pending: {complaint_metrics.pendingComplaints}
- Average Response Time: {complaint_metrics.averageResponseTimeHours} hours

Top Categories: {', '.join(list(complaint_metrics.complaintsByCategory.keys())[:3])}

Generate a brief with:
1. SUMMARY: 2-3 sentence overview
2. MAJOR ISSUES: List 2-3 key problems
3. TREND ANALYSIS: Brief trend assessment
4. RISK ASSESSMENT: Risk level and concerns
5. PRIORITY RECOMMENDATIONS: 2-3 actionable recommendations
6. CITIZEN IMPACT: How citizens are affected

Keep it concise, data-driven, and actionable."""
        
        return prompt

    def _parse_brief_response(
        self,
        ward_id: str,
        brief_text: str,
        ward_metrics: WardMetrics,
        complaint_metrics: ComplaintMetrics,
    ) -> WardBrief:
        """Parse AI response into structured brief."""
        # Extract sections (simple parsing)
        lines = brief_text.split("\n")
        
        summary = ""
        major_issues = []
        trend_analysis = ""
        risk_assessment = ""
        recommendations = []
        citizen_impact = ""
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Detect sections
            if "SUMMARY" in line.upper():
                current_section = "summary"
                continue
            elif "MAJOR ISSUES" in line.upper() or "KEY PROBLEMS" in line.upper():
                current_section = "issues"
                continue
            elif "TREND" in line.upper():
                current_section = "trend"
                continue
            elif "RISK" in line.upper():
                current_section = "risk"
                continue
            elif "RECOMMENDATION" in line.upper():
                current_section = "recommendations"
                continue
            elif "CITIZEN IMPACT" in line.upper():
                current_section = "impact"
                continue
            
            # Add content to sections
            if current_section == "summary":
                summary += line + " "
            elif current_section == "issues" and line.startswith(("-", "•", "*", "1", "2", "3")):
                major_issues.append(line.lstrip("-•*123. "))
            elif current_section == "trend":
                trend_analysis += line + " "
            elif current_section == "risk":
                risk_assessment += line + " "
            elif current_section == "recommendations" and line.startswith(("-", "•", "*", "1", "2", "3")):
                recommendations.append(line.lstrip("-•*123. "))
            elif current_section == "impact":
                citizen_impact += line + " "
        
        return WardBrief(
            wardId=ward_id,
            summary=summary.strip() or f"Ward {ward_id} analysis completed.",
            majorIssues=major_issues[:3],
            trendAnalysis=trend_analysis.strip() or "Trend analysis in progress.",
            riskAssessment=risk_assessment.strip() or "Risk assessment completed.",
            priorityRecommendations=recommendations[:3],
            citizenImpact=citizen_impact.strip() or "Citizen impact assessment completed.",
        )

    def _generate_fallback_brief(
        self,
        ward_id: str,
        ward_metrics: WardMetrics,
        complaint_metrics: ComplaintMetrics,
    ) -> WardBrief:
        """Generate fallback brief without AI."""
        # Determine major issues
        major_issues = []
        
        if ward_metrics.floodRiskScore > 70:
            major_issues.append("High flood risk detected")
        if ward_metrics.roadQualityScore < 40:
            major_issues.append("Poor road quality")
        if complaint_metrics.totalComplaints > 50:
            major_issues.append("High complaint volume")
        
        # Generate summary
        summary = (
            f"Ward {ward_id} has an overall infrastructure score of "
            f"{ward_metrics.overallInfrastructureScore:.1f}/100. "
            f"Received {complaint_metrics.totalComplaints} complaints in the last 24 hours "
            f"with a {complaint_metrics.resolutionRate:.1f}% resolution rate."
        )
        
        # Recommendations
        recommendations = []
        if ward_metrics.roadQualityScore < 50:
            recommendations.append("Prioritize road maintenance and repairs")
        if complaint_metrics.resolutionRate < 70:
            recommendations.append("Improve complaint resolution processes")
        if ward_metrics.floodRiskScore > 60:
            recommendations.append("Implement flood mitigation measures")
        
        return WardBrief(
            wardId=ward_id,
            summary=summary,
            majorIssues=major_issues,
            trendAnalysis="Monitoring ongoing trends in infrastructure and complaints.",
            riskAssessment=f"Overall risk level: {'High' if ward_metrics.overallInfrastructureScore < 50 else 'Moderate'}",
            priorityRecommendations=recommendations,
            citizenImpact="Citizens experiencing service delivery challenges in identified areas.",
        )
