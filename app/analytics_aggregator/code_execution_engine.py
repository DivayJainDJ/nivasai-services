"""Gemini Code Execution engine for analytics."""

from __future__ import annotations

import os
from typing import Any, Optional

import google.generativeai as genai

from app.config import settings
from app.shared.logging.logger import get_logger

logger = get_logger(__name__)


class CodeExecutionEngine:
    """Execute Python code and SQL queries using Gemini."""

    def __init__(self):
        """Initialize code execution engine."""
        self.model = None
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            # Use code execution model
            self.model = genai.GenerativeModel(
                "gemini-1.5-pro",
                tools="code_execution",
            )
            logger.info("code_execution_engine_initialized")
        except Exception as exc:
            logger.warning("code_execution_engine_init_failed", error=str(exc))

    def execute_analytics_query(self, query: str, context: dict[str, Any]) -> Optional[dict]:
        """
        Execute analytics query using Gemini Code Execution.
        
        Args:
            query: Natural language query
            context: Context data for analysis
        
        Returns:
            Analysis results
        """
        if not self.model:
            logger.warning("code_execution_not_available")
            return None
        
        try:
            # Build prompt with context
            prompt = f"""Analyze the following municipal data and answer the query.

Data Context:
{self._format_context(context)}

Query: {query}

Provide a structured analysis with key findings and metrics."""
            
            # Generate response with code execution
            response = self.model.generate_content(prompt)
            
            # Extract results
            result_text = response.text
            
            logger.info("analytics_query_executed", query=query[:50])
            
            return {
                "query": query,
                "analysis": result_text,
                "success": True,
            }
        
        except Exception as exc:
            logger.error("analytics_query_failed", error=str(exc))
            return {
                "query": query,
                "error": str(exc),
                "success": False,
            }

    def compute_trend(self, data_points: list[float], metric_name: str) -> dict:
        """Compute trend analysis using code execution."""
        if not self.model or not data_points:
            return {"trend": "unknown", "direction": "stable"}
        
        try:
            prompt = f"""Analyze this time series data for {metric_name}:
{data_points}

Calculate:
1. Trend direction (increasing/decreasing/stable)
2. Percentage change
3. Volatility assessment

Provide concise analysis."""
            
            response = self.model.generate_content(prompt)
            
            # Simple parsing
            text = response.text.lower()
            
            if "increasing" in text or "rising" in text:
                direction = "increasing"
            elif "decreasing" in text or "declining" in text:
                direction = "decreasing"
            else:
                direction = "stable"
            
            return {
                "trend": response.text,
                "direction": direction,
                "data_points": len(data_points),
            }
        
        except Exception as exc:
            logger.error("trend_computation_failed", error=str(exc))
            return {"trend": "unknown", "direction": "stable"}

    def detect_statistical_anomaly(
        self,
        current_value: float,
        historical_values: list[float],
        metric_name: str,
    ) -> dict:
        """Detect anomalies using statistical analysis."""
        if not self.model or not historical_values:
            return {"is_anomaly": False}
        
        try:
            prompt = f"""Perform statistical anomaly detection for {metric_name}.

Current value: {current_value}
Historical values: {historical_values}

Determine if current value is a statistical anomaly using:
- Standard deviation analysis
- Z-score calculation
- Threshold detection

Provide yes/no answer and explanation."""
            
            response = self.model.generate_content(prompt)
            text = response.text.lower()
            
            is_anomaly = "yes" in text or "anomaly" in text
            
            return {
                "is_anomaly": is_anomaly,
                "explanation": response.text,
                "current_value": current_value,
            }
        
        except Exception as exc:
            logger.error("anomaly_detection_failed", error=str(exc))
            return {"is_anomaly": False}

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context data for prompt."""
        lines = []
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                lines.append(f"{key}: {len(value) if isinstance(value, list) else 'object'}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
