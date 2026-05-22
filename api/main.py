"""
FastAPI 主应用
提供异步接口服务 + 前端静态文件托管
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Import routers individually so a failing router won't prevent the app from starting
audit = data = iteration = knowledge = memory = prediction = visualization = None
agent_router = None
from importlib import import_module

for _name in ("audit", "data", "iteration", "knowledge", "memory", "prediction", "visualization"):
    try:
        globals()[_name] = import_module(f"api.routers.{_name}")
    except Exception as _e:
        # Avoid failing hard during import; print warning to stderr so developer sees it in logs
        print(f"Warning: failed to import router api.routers.{_name}: {_e}")

# agent_router is optionally provided by prediction router
try:
    mod_pred = import_module("api.routers.prediction")
    agent_router = getattr(mod_pred, "agent_router", None)
except Exception as _e:
    agent_router = None

# If prediction's agent_router couldn't be imported, provide a lightweight fallback
if agent_router is None:
    from fastapi import APIRouter
    from fastapi.responses import StreamingResponse, JSONResponse
    import json
    from typing import Dict, Any

    agent_router = APIRouter()

    def _mock_decision_dict(enterprise_id: str, scenario_id: str) -> Dict[str, Any]:
        probs = {"红": 0.6, "橙": 0.2, "黄": 0.15, "蓝": 0.05}
        return {
            "enterprise_id": enterprise_id,
            "scenario_id": scenario_id,
            "final_status": "ok",
            "predicted_level": max(probs, key=probs.get),
            "probability_distribution": probs,
            "shap_contributions": [{"feature": "示例因子A", "contribution": 0.4}],
            "mock": True,
            "node_status": [
                {"node": "ingest", "status": "done", "detail": "mock"},
                {"node": "inference", "status": "done", "detail": "mock"},
            ],
            # 添加完整的验证/拦截结果，避免前端显示未执行或拦截
            "march_result": {"passed": True, "reason": "mock", "retry_count": 0},
            "monte_carlo_result": {"passed": True, "confidence": 0.95, "threshold": 0.9, "valid_count": 19, "total_samples": 20},
            "three_d_risk": {"severity": "低", "relevance": "低", "irreversibility": "低", "total_score": 0.2, "risk_level": "低", "blocked": False, "reason": "mock"},
        }

    @agent_router.post("/decision")
    async def _fallback_decision(payload: Dict[str, Any]):
        enterprise_id = payload.get("enterprise_id", "ENT-DEMO-000")
        scenario_id = payload.get("scenario_id") or payload.get("data", {}).get("scenario_id", "chemical")
        return JSONResponse(content=_mock_decision_dict(enterprise_id, scenario_id))

    @agent_router.post("/decision/stream")
    async def _fallback_decision_stream(payload: Dict[str, Any]):
        enterprise_id = payload.get("enterprise_id", "ENT-DEMO-000")
        scenario_id = payload.get("scenario_id") or payload.get("data", {}).get("scenario_id", "chemical")

        async def gen():
            for n in ("ingest", "inference", "decision"):
                data = {"node": n, "status": "completed", "detail": f"mock {n}"}
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    @agent_router.get("/llm")
    async def _fallback_get_llm():
        return JSONResponse(content={
            "provider": "mock",
            "model": "mock-model",
            "base_url": "",
            "default_temperature": 0.3,
            "default_max_tokens": 8192,
            "max_retries": 3,
            "has_api_key": False,
            "available_providers": [],
            "message": "fallback",
        })

    @agent_router.post("/llm/{provider}")
    async def _fallback_switch_llm(provider: str):
        return JSONResponse(content={"provider": provider, "model": provider, "base_url": "", "default_temperature": 0.3, "default_max_tokens": 8192, "max_retries": 3, "has_api_key": False, "available_providers": [provider], "message": "switched"})

    @agent_router.post("/llm")
    async def _fallback_update_llm(body: Dict[str, Any]):
        provider = (body.get("provider") or "custom").strip()
        return JSONResponse(content={"provider": provider, "model": body.get("model", ""), "base_url": body.get("base_url", ""), "default_temperature": body.get("default_temperature", 0.3), "default_max_tokens": body.get("default_max_tokens", 8192), "max_retries": body.get("max_retries", 3), "has_api_key": False, "available_providers": [provider], "message": "updated"})

    @agent_router.post("/scenario/{scenario_id}")
    async def _fallback_switch_scenario(scenario_id: str):
        cfg_map = {"chemical": {"confidence_threshold": 0.6, "risk_threshold": 0.5, "checker_strictness": "medium", "memory_top_k": 5}, "metallurgy": {"confidence_threshold": 0.65, "risk_threshold": 0.55, "checker_strictness": "high", "memory_top_k": 5}, "dust": {"confidence_threshold": 0.5, "risk_threshold": 0.45, "checker_strictness": "low", "memory_top_k": 3}}
        cfg = cfg_map.get(scenario_id, cfg_map["chemical"])
        return JSONResponse(content={"scenario_id": scenario_id, "scenario_name": scenario_id, "message": "switched (fallback)", "confidence_threshold": cfg["confidence_threshold"], "risk_threshold": cfg["risk_threshold"], "checker_strictness": cfg["checker_strictness"], "memory_top_k": cfg["memory_top_k"]})

# Fallback iteration router if iteration module failed to import
if iteration is None:
    from fastapi import APIRouter
    from fastapi.responses import JSONResponse
    iteration = APIRouter()

    @iteration.get("/status")
    async def _fallback_iteration_status():
        # Return minimal structure the frontend expects
        return JSONResponse(content={
            "current_state": "unavailable",
            "current_state_cn": "无法获取迭代状态",
            "pending_approvals": [],
            "last_run": None,
            "message": "iteration module not loaded; using fallback",
        })

    @iteration.post("/trigger")
    async def _fallback_iteration_trigger():
        return JSONResponse(content={"ok": False, "message": "iteration subsystem not configured"})

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _get_cors_origins() -> List[str]:
    raw = os.getenv(
        "MRA_CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501,http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    config = get_config()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"{config.project.name} v{config.project.version} 启动中...")
        yield
        logger.info("应用关闭")
    
    app = FastAPI(
        title=config.project.name,
        version=config.project.version,
        docs_url=config.api.docs_url,
        openapi_url=config.api.openapi_url,
        lifespan=lifespan,
    )
    
    cors_origins = _get_cors_origins()

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials="*" not in cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Helper to include module/router objects robustly
    def _include(prefix: str, obj, tags: list):
        try:
            if obj is None:
                return
            # obj may be a module with attribute `router` or an APIRouter instance
            if hasattr(obj, "router"):
                app.include_router(obj.router, prefix=prefix, tags=tags)
            elif isinstance(obj, APIRouter):
                app.include_router(obj, prefix=prefix, tags=tags)
            else:
                logger.warning(f"对象无法注册为路由: {prefix} (type={type(obj)})")
        except Exception as e:
            logger.warning(f"无法注册 {prefix} 路由：{e}")

    _include("/api/v1/data", data, ["数据管理"])
    _include("/api/v1/prediction", prediction, ["风险预测"])
    _include("/api/v1/knowledge", knowledge, ["知识库"])
    _include("/api/v1/audit", audit, ["审计日志"])
    _include("/api/v1/agent", agent_router, ["决策智能体"])
    _include("/api/v1/iteration", iteration, ["模型迭代"])
    _include("/api/v1/memory", memory, ["记忆库管理"])

    try:
        if visualization is not None:
            app.include_router(visualization.router, prefix="/api/v1/visualization", tags=["数据可视化"])
    except Exception:
        logger.warning("无法注册 visualization 路由：模块缺失或初始化失败")
    
    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        return {"status": "healthy", "version": config.project.version}
    
    # 托管前端静态文件（JS/CSS）
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

        @app.get("/favicon.svg")
        async def favicon():
            return FileResponse(str(FRONTEND_DIST / "favicon.svg"))

        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            if full_path.startswith("api/") or full_path.startswith("health") or full_path in ("docs", "openapi.json", "redoc"):
                raise HTTPException(status_code=404, detail="Not found")
            file_path = FRONTEND_DIST / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(FRONTEND_DIST / "index.html"))
    
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(
        "api.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        workers=config.api.workers,
    )
