from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None

from ..config import settings
from .mlops_alerts import get_mlops_alerts

class MLOpsTracker:
    def __init__(self, tracking_uri: Optional[str] = None):
        if not MLFLOW_AVAILABLE:
            self.enabled = False
            return
        
        self.enabled = getattr(settings, 'mlops_enabled', True)
        
        if not self.enabled:
            return
        
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        else:
            mlflow_dir = Path(settings.data_dir) / "mlruns"
            mlflow_dir.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                mlflow.set_tracking_uri(f"file:///{str(mlflow_dir.absolute()).replace(chr(92), '/')}")
            else:
                mlflow.set_tracking_uri(f"file://{mlflow_dir.absolute()}")
        
        try:
            self.client = MlflowClient()
        except Exception:
            self.client = None
        self.experiment_name = getattr(settings, 'mlops_experiment_name', 'syro_rag')
        
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                mlflow.create_experiment(self.experiment_name)
        except Exception:
            pass
    
    def log_rag_query(
        self,
        query: str,
        organization_id: int,
        retrieval_method: str = "hybrid",
        num_sources: int = 0,
        avg_source_score: float = 0.0,
        response_time_ms: float = 0.0,
        token_usage: int = 0,
        domain: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        if not self.enabled:
            return None
        
        try:
            mlflow.set_experiment(self.experiment_name)
            
            with mlflow.start_run(run_name=f"rag_query_{int(time.time())}"):
                mlflow.log_param("organization_id", organization_id)
                mlflow.log_param("retrieval_method", retrieval_method)
                mlflow.log_param("domain", domain or settings.domain)
                mlflow.log_param("query_length", len(query))
                
                mlflow.log_metric("num_sources", num_sources)
                mlflow.log_metric("avg_source_score", avg_source_score)
                mlflow.log_metric("response_time_ms", response_time_ms)
                mlflow.log_metric("token_usage", token_usage)
                
                for key, value in kwargs.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(key, value)
                    else:
                        mlflow.log_param(key, str(value))
                
                query_file = Path(settings.data_dir) / "tmp" / f"query_{int(time.time())}.txt"
                query_file.parent.mkdir(parents=True, exist_ok=True)
                with open(query_file, "w", encoding="utf-8") as f:
                    f.write(query)
                mlflow.log_artifact(str(query_file))
                query_file.unlink()
                
                try:
                    alerts = get_mlops_alerts()
                    metrics_dict = {
                        "response_time_ms": response_time_ms,
                        "token_usage": token_usage,
                        "num_sources": num_sources,
                        "avg_source_score": avg_source_score,
                    }
                    alerts.check_metrics(metrics_dict)
                except Exception:
                    pass
                
                return mlflow.active_run().info.run_id
        except Exception:
            return None
    
    def log_retrieval_experiment(
        self,
        experiment_name: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        tags: Optional[dict[str, str]] = None
    ) -> Optional[str]:
        if not self.enabled:
            return None
        
        try:
            mlflow.set_experiment(experiment_name)
            
            with mlflow.start_run(run_name=f"experiment_{int(time.time())}"):
                for key, value in params.items():
                    mlflow.log_param(key, value)
                
                for key, value in metrics.items():
                    mlflow.log_metric(key, value)
                
                if tags:
                    for key, value in tags.items():
                        mlflow.set_tag(key, value)
                
                return mlflow.active_run().info.run_id
        except Exception:
            return None
    
    def log_model_performance(
        self,
        model_name: str,
        model_version: str,
        metrics: dict[str, float],
        metadata: Optional[dict[str, Any]] = None
    ):
        if not self.enabled:
            return
        
        try:
            mlflow.set_experiment(self.experiment_name)
            
            with mlflow.start_run(run_name=f"model_{model_name}_{model_version}"):
                mlflow.log_param("model_name", model_name)
                mlflow.log_param("model_version", model_version)
                
                for key, value in metrics.items():
                    mlflow.log_metric(key, value)
                
                if metadata:
                    for key, value in metadata.items():
                        mlflow.log_param(f"metadata_{key}", str(value))
        except Exception:
            pass
    
    def log_document_ingestion(
        self,
        document_id: int,
        organization_id: int,
        num_chunks: int,
        ingestion_time_ms: float,
        document_size_chars: int,
        metadata: Optional[dict[str, Any]] = None
    ):
        if not self.enabled:
            return
        
        try:
            mlflow.set_experiment(self.experiment_name)
            
            with mlflow.start_run(run_name=f"ingestion_doc_{document_id}"):
                mlflow.log_param("document_id", document_id)
                mlflow.log_param("organization_id", organization_id)
                mlflow.log_metric("num_chunks", num_chunks)
                mlflow.log_metric("ingestion_time_ms", ingestion_time_ms)
                mlflow.log_metric("document_size_chars", document_size_chars)
                mlflow.log_metric("avg_chunk_size", document_size_chars / max(num_chunks, 1))
                
                if metadata:
                    for key, value in metadata.items():
                        mlflow.log_param(f"doc_{key}", str(value))
                
                try:
                    alerts = get_mlops_alerts()
                    metrics_dict = {
                        "ingestion_time_ms": ingestion_time_ms,
                        "num_chunks": num_chunks,
                    }
                    alerts.check_metrics(metrics_dict)
                except Exception:
                    pass
        except Exception:
            pass
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        organization_id: int | None = None,
        context: dict[str, Any] | None = None,
    ):
        if not self.enabled:
            return
        
        try:
            mlflow.set_experiment(self.experiment_name)
            
            with mlflow.start_run(run_name=f"error_{error_type}_{int(time.time())}"):
                mlflow.log_param("error_type", error_type)
                mlflow.log_param("error_message", error_message)
                mlflow.log_metric("error_count", 1)
                
                if organization_id:
                    mlflow.log_param("organization_id", organization_id)
                
                if context:
                    for key, value in context.items():
                        mlflow.log_param(f"context_{key}", str(value))
                
                mlflow.set_tag("type", "error")
        except Exception:
            pass
    
    def log_warning(
        self,
        warning_type: str,
        warning_message: str,
        organization_id: int | None = None,
        context: dict[str, Any] | None = None,
    ):
        if not self.enabled:
            return
        
        try:
            mlflow.set_experiment(self.experiment_name)
            
            with mlflow.start_run(run_name=f"warning_{warning_type}_{int(time.time())}"):
                mlflow.log_param("warning_type", warning_type)
                mlflow.log_param("warning_message", warning_message)
                mlflow.log_metric("warning_count", 1)
                
                if organization_id:
                    mlflow.log_param("organization_id", organization_id)
                
                if context:
                    for key, value in context.items():
                        mlflow.log_param(f"context_{key}", str(value))
                
                mlflow.set_tag("type", "warning")
        except Exception:
            pass
    
    def get_latest_metrics(self, limit: int = 10, include_errors: bool = True) -> list[dict[str, Any]]:
        if not self.enabled or self.client is None:
            return []
        
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                return []
            
            runs = self.client.search_runs(
                experiment_ids=[experiment.experiment_id],
                max_results=limit,
                order_by=["start_time DESC"]
            )
            
            results = []
            for run in runs:
                run_type = run.data.tags.get("type", "query")
                if not include_errors and run_type in ("error", "warning"):
                    continue
                
                results.append({
                    "run_id": run.info.run_id,
                    "start_time": run.info.start_time,
                    "status": run.info.status,
                    "type": run_type,
                    "metrics": run.data.metrics,
                    "params": run.data.params,
                    "tags": run.data.tags,
                })
            
            return results
        except Exception:
            return []

_tracker: Optional[MLOpsTracker] = None

def get_mlops_tracker() -> MLOpsTracker:
    global _tracker
    if _tracker is None:
        tracking_uri = getattr(settings, 'mlflow_tracking_uri', None)
        _tracker = MLOpsTracker(tracking_uri=tracking_uri)
    return _tracker

