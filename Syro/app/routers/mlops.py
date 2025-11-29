from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

from ..dependencies import get_current_user, require_active_org
from ..services.mlops_tracker import get_mlops_tracker
from ..services.mlops_alerts import get_mlops_alerts
from ..services.chat import build_answer
from ..config import settings

router = APIRouter(prefix="/mlops", tags=["mlops"])

@router.get("/metrics")
def get_metrics(
    limit: int = 10,
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
):
    tracker = get_mlops_tracker()
    if not tracker.enabled:
        return {
            "enabled": False,
            "message": "MLOps tracking is disabled",
            "metrics": []
        }
    
    metrics = tracker.get_latest_metrics(limit=limit)
    
    return {
        "enabled": True,
        "experiment_name": tracker.experiment_name,
        "total_runs": len(metrics),
        "metrics": metrics
    }

@router.get("/stats")
def get_stats(
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
):
    tracker = get_mlops_tracker()
    if not tracker.enabled:
        return {
            "enabled": False,
            "message": "MLOps tracking is disabled"
        }
    
    metrics = tracker.get_latest_metrics(limit=100)
    
    if not metrics:
        return {
            "enabled": True,
            "total_runs": 0,
            "stats": {}
        }
    
    # Aggregate statistics
    response_times = [m["metrics"].get("response_time_ms", 0) for m in metrics if "response_time_ms" in m["metrics"]]
    token_usages = [m["metrics"].get("token_usage", 0) for m in metrics if "token_usage" in m["metrics"]]
    num_sources = [m["metrics"].get("num_sources", 0) for m in metrics if "num_sources" in m["metrics"]]
    avg_scores = [m["metrics"].get("avg_source_score", 0) for m in metrics if "avg_source_score" in m["metrics"]]
    
    stats = {}
    
    if response_times:
        stats["response_time_ms"] = {
            "avg": sum(response_times) / len(response_times),
            "min": min(response_times),
            "max": max(response_times),
        }
    
    if token_usages:
        stats["token_usage"] = {
            "avg": sum(token_usages) / len(token_usages),
            "min": min(token_usages),
            "max": max(token_usages),
            "total": sum(token_usages),
        }
    
    if num_sources:
        stats["num_sources"] = {
            "avg": sum(num_sources) / len(num_sources),
            "min": min(num_sources),
            "max": max(num_sources),
        }
    
    if avg_scores:
        stats["avg_source_score"] = {
            "avg": sum(avg_scores) / len(avg_scores),
            "min": min(avg_scores),
            "max": max(avg_scores),
        }
    
    return {
        "enabled": True,
        "total_runs": len(metrics),
        "stats": stats
    }

@router.post("/feedback")
def log_feedback(
    query_id: str | None = None,
    rating: int | None = None,
    feedback_text: str | None = None,
    helpful: bool | None = None,
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
):
    tracker = get_mlops_tracker()
    if not tracker.enabled:
        return {
            "enabled": False,
            "message": "MLOps tracking is disabled"
        }
    
    # Log feedback as a custom metric
    try:
        metrics = {}
        if rating is not None:
            metrics["user_rating"] = float(rating)
        if helpful is not None:
            metrics["helpful"] = 1.0 if helpful else 0.0
        
        if metrics:
            tracker.log_retrieval_experiment(
                experiment_name="user_feedback",
                params={
                    "query_id": query_id or "unknown",
                    "organization_id": str(org["id"]),
                    "feedback_text": feedback_text or "",
                },
                metrics=metrics,
                tags={"type": "user_feedback", "organization_id": str(org["id"])},
            )
        
        return {
            "success": True,
            "message": "Feedback logged successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/alerts/thresholds")
def get_alert_thresholds(
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
):
    alerts = get_mlops_alerts()
    
    thresholds = {}
    for metric_name, threshold in alerts.thresholds.items():
        thresholds[metric_name] = {
            "warning_threshold": threshold.warning_threshold,
            "critical_threshold": threshold.critical_threshold,
            "comparison": threshold.comparison,
        }
    
    return {
        "enabled": alerts.enabled,
        "email_enabled": alerts.email_enabled,
        "webhook_enabled": alerts.webhook_enabled,
        "thresholds": thresholds,
    }

@router.post("/alerts/test")
def test_alert(
    metric_name: str,
    value: float,
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
):
    alerts = get_mlops_alerts()
    if not alerts.enabled:
        return {
            "enabled": False,
            "message": "MLOps alerts are disabled"
        }
    
    result = alerts.check_metrics({metric_name: value})
    
    return {
        "metric": metric_name,
        "value": value,
        "alerts_triggered": result,
    }

@router.get("/errors")
def get_errors(
    limit: int = 20,
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
):
    tracker = get_mlops_tracker()
    if not tracker.enabled:
        return {
            "enabled": False,
            "message": "MLOps tracking is disabled",
            "errors": [],
            "warnings": []
        }
    
    # Get all runs including errors/warnings
    all_runs = tracker.get_latest_metrics(limit=limit * 2, include_errors=True)
    
    errors = [r for r in all_runs if r.get("type") == "error"][:limit]
    warnings = [r for r in all_runs if r.get("type") == "warning"][:limit]
    
    return {
        "enabled": True,
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }

@router.get("/export")
def export_metrics(
    format: str = "json",
    limit: int = 100,
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
):
    tracker = get_mlops_tracker()
    if not tracker.enabled:
        return {
            "enabled": False,
            "message": "MLOps tracking is disabled"
        }
    
    metrics = tracker.get_latest_metrics(limit=limit, include_errors=False)
    
    if format == "csv":
        # Convert to CSV format
        import csv
        import io
        
        if not metrics:
            return {"format": "csv", "data": ""}
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        all_keys = set()
        for m in metrics:
            all_keys.update(m["metrics"].keys())
            all_keys.update(m["params"].keys())
        
        header = ["run_id", "start_time", "status", "type"] + sorted(all_keys)
        writer.writerow(header)
        
        # Data rows
        for m in metrics:
            row = [m["run_id"], m["start_time"], m["status"], m.get("type", "query")]
            for key in sorted(all_keys):
                if key in m["metrics"]:
                    row.append(m["metrics"][key])
                elif key in m["params"]:
                    row.append(m["params"][key])
                else:
                    row.append("")
            writer.writerow(row)
        
        return {
            "format": "csv",
            "data": output.getvalue(),
            "content_type": "text/csv"
        }
    
    # Default: JSON
    return {
        "format": "json",
        "data": metrics,
        "total": len(metrics)
    }

class BenchmarkRequest(BaseModel):
    queries: list[str]
    modes: list[str] = ["fast", "quality"]
    include_sources: bool = False

@router.post("/benchmark")
def run_benchmark(
    payload: BenchmarkRequest = Body(...),
    user = Depends(get_current_user),
    org = Depends(require_active_org()),
):
    tracker = get_mlops_tracker()
    results = {
        "timestamp": time.time(),
        "config": {
            "llm_provider": settings.llm_provider,
            "chat_model": settings.chat_model,
            "embeddings_model": settings.embeddings_model,
            "enable_reranking": settings.enable_reranking,
            "retrieval_top_k": settings.retrieval_top_k,
            "rerank_top_k": settings.rerank_top_k,
            "performance_mode": settings.performance_mode,
        },
        "results": [],
    }
    
    original_mode = settings.performance_mode
    
    for mode in payload.modes:
        if mode not in ["fast", "quality"]:
            continue
        
        # Temporarily set performance mode
        settings.performance_mode = mode
        settings.apply_performance_mode()
        
        for query in payload.queries:
            try:
                start_time = time.time()
                answer, usage, sources = build_answer(
                    organization_id=org["id"],
                    query=query,
                    include_sources=payload.include_sources,
                )
                latency_ms = (time.time() - start_time) * 1000
                
                result = {
                    "query": query,
                    "mode": mode,
                    "latency_ms": round(latency_ms, 2),
                    "token_usage": usage,
                    "answer_length": len(answer),
                    "num_sources": len(sources) if payload.include_sources else 0,
                    "success": True,
                }
                
                # Log to MLflow if enabled
                if tracker.enabled:
                    avg_score = sum(s.get("score", 0.0) for s in sources) / max(len(sources), 1) if sources else 0.0
                    tracker.log_retrieval_experiment(
                        experiment_name="benchmark",
                        params={
                            "query": query,
                            "mode": mode,
                            "organization_id": str(org["id"]),
                        },
                        metrics={
                            "latency_ms": latency_ms,
                            "token_usage": usage,
                            "num_sources": len(sources),
                            "avg_source_score": avg_score,
                        },
                        tags={"type": "benchmark", "mode": mode},
                    )
                
                results["results"].append(result)
            except Exception as e:
                results["results"].append({
                    "query": query,
                    "mode": mode,
                    "latency_ms": 0,
                    "error": str(e),
                    "success": False,
                })
        
        # Restore original mode
        settings.performance_mode = original_mode
        settings.apply_performance_mode()
    
    # Calculate statistics
    stats = {}
    for mode in payload.modes:
        mode_results = [r for r in results["results"] if r.get("mode") == mode and r.get("success")]
        if mode_results:
            latencies = [r["latency_ms"] for r in mode_results]
            stats[mode] = {
                "count": len(mode_results),
                "latency_avg_ms": round(sum(latencies) / len(latencies), 2),
                "latency_min_ms": round(min(latencies), 2),
                "latency_max_ms": round(max(latencies), 2),
                "latency_p50_ms": round(sorted(latencies)[len(latencies) // 2], 2),
                "latency_p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if len(latencies) > 1 else round(latencies[0], 2),
            }
    
    results["statistics"] = stats
    
    return results

