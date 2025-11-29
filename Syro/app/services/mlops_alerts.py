from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False

import httpx

from ..config import settings

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertThreshold:
    def __init__(
        self,
        metric_name: str,
        warning_threshold: float,
        critical_threshold: float,
        comparison: str = "greater",
        window_size: int = 5,
    ):
        self.metric_name = metric_name
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.comparison = comparison
        self.window_size = window_size
    
    def check(self, value: float) -> Optional[AlertLevel]:
        if self.comparison == "greater":
            if value >= self.critical_threshold:
                return AlertLevel.CRITICAL
            elif value >= self.warning_threshold:
                return AlertLevel.WARNING
        elif self.comparison == "less":
            if value <= self.critical_threshold:
                return AlertLevel.CRITICAL
            elif value <= self.warning_threshold:
                return AlertLevel.WARNING
        elif self.comparison == "equal":
            if value == self.critical_threshold:
                return AlertLevel.CRITICAL
            elif value == self.warning_threshold:
                return AlertLevel.WARNING
        
        return None

class MLOpsAlerts:
    DEFAULT_THRESHOLDS = {
        "response_time_ms": AlertThreshold(
            metric_name="response_time_ms",
            warning_threshold=3000.0,
            critical_threshold=5000.0,
            comparison="greater",
        ),
        "avg_source_score": AlertThreshold(
            metric_name="avg_source_score",
            warning_threshold=0.6,
            critical_threshold=0.5,
            comparison="less",
        ),
        "num_sources": AlertThreshold(
            metric_name="num_sources",
            warning_threshold=2,
            critical_threshold=1,
            comparison="less",
        ),
        "token_usage": AlertThreshold(
            metric_name="token_usage",
            warning_threshold=2000,
            critical_threshold=3000,
            comparison="greater",
        ),
    }
    
    def __init__(self):
        self.enabled = getattr(settings, 'mlops_alerts_enabled', False)
        self.email_enabled = getattr(settings, 'mlops_alerts_email_enabled', False)
        self.webhook_enabled = getattr(settings, 'mlops_alerts_webhook_enabled', False)
        
        # Email settings
        self.email_smtp_host = getattr(settings, 'mlops_alerts_smtp_host', None)
        self.email_smtp_port = getattr(settings, 'mlops_alerts_smtp_port', 587)
        self.email_smtp_user = getattr(settings, 'mlops_alerts_smtp_user', None)
        self.email_smtp_password = getattr(settings, 'mlops_alerts_smtp_password', None)
        self.email_from = getattr(settings, 'mlops_alerts_email_from', None)
        self.email_to = getattr(settings, 'mlops_alerts_email_to', None)
        
        self.webhook_url = getattr(settings, 'mlops_alerts_webhook_url', None)
        
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        self._load_custom_thresholds()
    
    def _load_custom_thresholds(self):
        pass
    
    def check_metrics(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        
        alerts = []
        
        for metric_name, threshold in self.thresholds.items():
            if metric_name not in metrics:
                continue
            
            value = metrics[metric_name]
            if not isinstance(value, (int, float)):
                continue
            
            alert_level = threshold.check(value)
            if alert_level:
                alerts.append({
                    "metric": metric_name,
                    "value": value,
                    "level": alert_level.value,
                    "threshold": threshold.critical_threshold if alert_level == AlertLevel.CRITICAL else threshold.warning_threshold,
                    "timestamp": datetime.now().isoformat(),
                })
        
        if alerts:
            self._send_alerts(alerts, metrics)
        
        return alerts
    
    def _send_alerts(self, alerts: list[dict[str, Any]], metrics: dict[str, Any]):
        if self.email_enabled and self.email_from and self.email_to:
            self._send_email_alert(alerts, metrics)
        
        if self.webhook_enabled and self.webhook_url:
            self._send_webhook_alert(alerts, metrics)
    
    def _send_email_alert(self, alerts: list[dict[str, Any]], metrics: dict[str, Any]):
        if not SMTP_AVAILABLE or not self.email_smtp_host:
            print("Warning: SMTP not available or not configured")
            return
        
        try:
            critical_alerts = [a for a in alerts if a["level"] == "critical"]
            warning_alerts = [a for a in alerts if a["level"] == "warning"]
            
            if critical_alerts:
                subject = f"CRITICAL MLOps Alert - {len(critical_alerts)} critical issue(s)"
                level = "CRITICAL"
            else:
                subject = f"MLOps Warning - {len(warning_alerts)} warning(s)"
                level = "WARNING"
            
            body = f"""
MLOps Alert - {level}

Timestamp: {datetime.now().isoformat()}

Alerts:
{json.dumps(alerts, indent=2)}

Current Metrics:
{json.dumps(metrics, indent=2)}

Please review the MLOps dashboard for more details.
"""
            
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = self.email_to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.email_smtp_host, self.email_smtp_port) as server:
                if self.email_smtp_user and self.email_smtp_password:
                    server.starttls()
                    server.login(self.email_smtp_user, self.email_smtp_password)
                server.send_message(msg)
            
            print(f"MLOps alert email sent: {subject}")
        except Exception as e:
            print(f"Warning: Failed to send email alert: {e}")
    
    def _send_webhook_alert(self, alerts: list[dict[str, Any]], metrics: dict[str, Any]):
        if not self.webhook_url:
            return
        
        try:
            payload = {
                "timestamp": datetime.now().isoformat(),
                "alerts": alerts,
                "metrics": metrics,
            }
            
            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            
            print(f"MLOps alert webhook sent: {len(alerts)} alert(s)")
        except Exception as e:
            print(f"Warning: Failed to send webhook alert: {e}")
    
    def add_threshold(self, threshold: AlertThreshold):
        self.thresholds[threshold.metric_name] = threshold
    
    def remove_threshold(self, metric_name: str):
        if metric_name in self.thresholds:
            del self.thresholds[metric_name]

_alerts: Optional[MLOpsAlerts] = None

def get_mlops_alerts() -> MLOpsAlerts:
    global _alerts
    if _alerts is None:
        _alerts = MLOpsAlerts()
    return _alerts

