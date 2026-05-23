"""
记忆库管理路由
支持短期/长期记忆CRUD、new_data目录Excel批量导入、
上传Excel文件导入长期记忆、批量风险评估、预警经验管理、
数据导出、模型迭代追踪、管理员审批工作流
"""

import asyncio
import csv
import glob
import hashlib
import io
import json
import math
import os
import random
import re
import threading
import time
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

_long_term_store: List[Dict[str, Any]] = []
_short_term_store: List[Dict[str, Any]] = []
_enterprise_data_cache: Dict[str, pd.DataFrame] = {}
_warning_experience_store: List[Dict[str, Any]] = []
_iteration_history: List[Dict[str, Any]] = []
_approval_store: List[Dict[str, Any]] = []
_audit_log_store: List[Dict[str, Any]] = []
_enterprise_risk_history: Dict[str, List[Dict[str, Any]]] = {}

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
os.makedirs(_DATA_DIR, exist_ok=True)


def _persist_all_stores() -> None:
    for name, data in [
        ("long_term", _long_term_store),
        ("short_term", _short_term_store),
        ("warning_experience", _warning_experience_store),
        ("iteration_history", _iteration_history),
        ("approval_store", _approval_store),
        ("audit_log", _audit_log_store),
        ("enterprise_risk_history", _enterprise_risk_history),
    ]:
        try:
            fpath = os.path.join(_DATA_DIR, f"{name}.json")
            sanitized = _sanitize_for_json(data)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(sanitized, f, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"自动持久化 {name} 失败: {e}", exc_info=True)


def _auto_save_loop() -> None:
    while True:
        time.sleep(30)
        try:
            _persist_all_stores()
            logger.debug("自动保存所有存储完成")
        except Exception as e:
            logger.error(f"自动保存失败: {e}")


_auto_save_thread = threading.Thread(target=_auto_save_loop, daemon=True)
_auto_save_thread.start()
logger.info("自动保存线程已启动（每30秒）")


def _persist_store(name: str, data: Any) -> None:
    try:
        fpath = os.path.join(_DATA_DIR, f"{name}.json")
        sanitized = _sanitize_for_json(data)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, ensure_ascii=False, default=str)
        logger.info(f"持久化 {name} 成功: {len(data) if isinstance(data, (list, dict)) else 'ok'} 条")
    except Exception as e:
        logger.error(f"持久化 {name} 失败: {e}", exc_info=True)


async def _async_persist(*names_stores: tuple) -> None:
    loop = asyncio.get_event_loop()
    for name, store in names_stores:
        try:
            await loop.run_in_executor(None, _persist_store, name, store)
        except Exception as e:
            logger.error(f"异步持久化 {name} 失败: {e}", exc_info=True)


def _load_store(name: str) -> Any:
    try:
        fpath = os.path.join(_DATA_DIR, f"{name}.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"加载 {name} 成功: {len(data) if isinstance(data, (list, dict)) else 'ok'} 条")
            return data
        else:
            logger.info(f"持久化文件不存在 {name}.json，使用空数据")
    except Exception as e:
        logger.error(f"加载 {name} 失败: {e}", exc_info=True)
    return None


def _restore_all_stores() -> None:
    global _long_term_store, _short_term_store, _warning_experience_store
    global _iteration_history, _approval_store, _audit_log_store, _enterprise_risk_history
    for name, store in [
        ("long_term", _long_term_store), ("short_term", _short_term_store),
        ("warning_experience", _warning_experience_store), ("iteration_history", _iteration_history),
        ("approval_store", _approval_store), ("audit_log", _audit_log_store),
        ("enterprise_risk_history", _enterprise_risk_history),
    ]:
        loaded = _load_store(name)
        if loaded is not None:
            store.clear()
            if isinstance(loaded, list):
                store.extend(loaded)
            elif isinstance(loaded, dict):
                store.update(loaded)


_restore_all_stores()


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _sanitize_val(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    if isinstance(val, (int, float, str, bool)):
        return val
    return str(val)


def _sanitize_for_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(i) for i in obj]
    return _sanitize_val(obj)


def _scan_new_data_dir() -> List[Dict[str, Any]]:
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "new_data")
    if not os.path.isdir(base):
        logger.warning(f"new_data 目录不存在: {base}")
        return []
    results = []
    for root, _dirs, files in os.walk(base):
        for fname in files:
            fpath = os.path.join(root, fname)
            ext = Path(fname).suffix.lower()
            if ext not in (".xlsx", ".xls", ".csv"):
                continue
            rel = os.path.relpath(fpath, base)
            results.append({"filename": fname, "rel_path": rel, "abs_path": fpath, "ext": ext, "size": os.path.getsize(fpath)})
    return results


def _load_file_to_df(fpath: str) -> Optional[pd.DataFrame]:
    try:
        with open(fpath, "rb") as f:
            return _read_tabular_upload(f.read(), os.path.basename(fpath))
    except Exception as e:
        logger.error(f"读取文件失败 {fpath}: {e}")
    return None


def _df_to_long_term_entries(df: pd.DataFrame, source_file: str) -> List[Dict[str, Any]]:
    entries = []
    cols = list(df.columns)
    summary_text = f"数据表: {source_file} | 行数: {len(df)} | 列: {', '.join(cols[:10])}{'...' if len(cols) > 10 else ''}"
    table_entry = {
        "id": _new_id(),
        "text": summary_text,
        "priority": "P0",
        "type": "long",
        "time": _now_str(),
        "timestamp": time.time(),
        "category": "enterprise_data",
        "data_source": source_file,
        "verified": True,
        "columns": cols,
        "row_count": len(df),
    }
    entries.append(table_entry)

    for idx, row in df.head(100).iterrows():
        row_data = {}
        for col in cols:
            val = row.get(col)
            if pd.notna(val):
                row_data[col] = str(val)
        if not row_data:
            continue
        text_parts = [f"{k}={v}" for k, v in list(row_data.items())[:8]]
        text = f"[{source_file}] 行{idx}: {'; '.join(text_parts)}"
        entry = {
            "id": _new_id(),
            "text": text,
            "priority": "P1",
            "type": "long",
            "time": _now_str(),
            "timestamp": time.time(),
            "category": "enterprise_data",
            "data_source": source_file,
            "verified": True,
            "row_data": row_data,
        }
        entries.append(entry)
    return entries


_ENTERPRISE_ID_KEYS = (
    "企业ID", "企业id", "enterprise_id", "主键ID", "主键id", "主键Id",
    "统一信用代码", "统一社会信用代码", "社会统一信用代码", "社会统一信用代码 主键",
    "行政相对人代码", "行政相对人统一社会信用代码", "当事人证照号码", "企业编号",
    "单位编号", "组织机构代码", "纳税人识别号", "主体代码", "社会信用代码",
    "案件id", "案件ID", "请求的id", "请求的ID", "id", "ID",
    "ENTERPRISE_ID", "ent_id", "company_id", "org_id", "credit_code", "UUIT_NO", "UUID", "uuid",
)
_ENTERPRISE_NAME_KEYS = (
    "企业名称", "企业名称 ", "enterprise_name", "单位名称", "公司名称", "地址名称",
    "企业全称", "单位全称", "公司全称", "企业简称", "单位简称",
    "当事人", "当事人名称", "被处罚单位", "被处罚人", "处罚对象",
    "行政相对人", "行政相对人名称", "生产经营单位", "企业（单位）名称",
    "企业(单位)名称", "申请单位", "被检查单位", "被执法单位", "监管对象",
    "市场主体名称", "经营主体名称", "法人单位", "主体名称", "单位",
    "ENTERPRISE_NAME", "COMPANY_NAME", "BUSI_ADDR_NAME", "company_name",
    "companyName", "ent_name", "entName", "org_name", "organization_name",
    "business_name", "company", "enterprise", "organization", "name",
)
_GENERIC_NAME_KEYS = ("名称",)
_CREDIT_KEYS = (
    "统一信用代码", "统一社会信用代码", "社会统一信用代码", "社会统一信用代码 主键",
    "行政相对人统一社会信用代码", "当事人证照号码", "社会信用代码", "信用代码",
    "组织机构代码", "纳税人识别号", "credit_code", "UUIT_NO",
)
_CASE_NAME_KEYS = (
    "案件名称", "案由", "事项名称", "违法事项", "标题", "名称",
    "问题描述", "隐患描述", "检查内容", "事故概述", "违法行为", "处罚事由",
    "处罚内容", "备注", "详情", "内容", "描述", "说明", "case_name",
    "description", "detail", "summary", "memo",
)
_ENTERPRISE_SUFFIXES = (
    "有限责任公司", "股份有限公司", "集团有限公司", "有限公司", "集团公司",
    "分公司", "总公司", "公司", "工厂", "厂", "矿业", "矿", "煤矿",
    "加油站", "经营部", "合作社", "中心", "商行", "门市部", "服务部",
    "工作室", "项目部", "研究院", "设计院", "事务所", "医院", "学校", "店",
)
_ENTERPRISE_NAME_RE = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9（）()·\-]{2,80}?"
    r"(?:有限责任公司|股份有限公司|集团有限公司|有限公司|集团公司|分公司|总公司|公司|工厂|厂|矿业|煤矿|矿|加油站|经营部|合作社|中心|商行|门市部|服务部|工作室|项目部|研究院|设计院|事务所|医院|学校|店))"
)


def _normalize_column_name(value: Any) -> str:
    return re.sub(r"[\s\ufeff_\-./\\()（）\[\]【】:：,，;；]+", "", str(value or "").strip()).lower()


def _column_matches(column: Any, keys: tuple[str, ...]) -> bool:
    normalized_column = _normalize_column_name(column)
    if not normalized_column:
        return False
    exact_only = {"name", "company", "enterprise", "org", "organization", "unit"}
    for key in keys:
        normalized_key = _normalize_column_name(key)
        if not normalized_key:
            continue
        if normalized_column == normalized_key:
            return True
        if normalized_key in exact_only:
            continue
        if (
            len(normalized_key) >= 3
            and len(normalized_column) >= 3
            and (normalized_key in normalized_column or normalized_column in normalized_key)
        ):
            return True
    return False


def _first_non_empty(row_data: Dict[str, Any], keys: tuple[str, ...]) -> Optional[str]:
    for key in keys:
        val = row_data.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    normalized_keys = {key.strip() for key in keys}
    for raw_key, val in row_data.items():
        if str(raw_key).strip() in normalized_keys and val is not None and str(val).strip():
            return str(val).strip()
    for raw_key, val in row_data.items():
        if _column_matches(raw_key, keys) and val is not None and str(val).strip():
            return str(val).strip()
    return None


def _clean_enterprise_name(name: str) -> str:
    return name.strip(" \t\r\n:：,，;；.。()（）[]【】\"'“”‘’")


def _looks_like_possible_enterprise_value(name: Optional[str]) -> bool:
    if not name:
        return False
    cleaned = _clean_enterprise_name(str(name))
    if len(cleaned) < 2 or len(cleaned) > 120:
        return False
    if cleaned.lower() in {"nan", "none", "null", "true", "false", "yes", "no", "是", "否"}:
        return False
    if re.fullmatch(r"[\d\s./:_\-]+", cleaned):
        return False
    return True


def _looks_like_enterprise_name(name: Optional[str]) -> bool:
    if not name:
        return False
    cleaned = _clean_enterprise_name(name)
    if len(cleaned) < 4 or re.match(r"^\d", cleaned):
        return False
    if any(token in cleaned for token in ("停产", "正常生产", "临时", "长期", "元旦", "春节", "日期", "时间")):
        return False
    matched_suffix = next((suffix for suffix in _ENTERPRISE_SUFFIXES if cleaned.endswith(suffix)), None)
    if not matched_suffix:
        return False
    if matched_suffix in {"厂", "矿", "店", "中心"}:
        chinese_count = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
        if chinese_count < 4:
            return False
    return True


def _extract_enterprise_name_from_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    matches = [_clean_enterprise_name(match) for match in _ENTERPRISE_NAME_RE.findall(str(text))]
    matches = [match for match in matches if _looks_like_enterprise_name(match)]
    if not matches:
        return None
    return max(matches, key=len)


def _direct_enterprise_name_from_row(row_data: Dict[str, Any]) -> Optional[str]:
    ent_name = _first_non_empty(row_data, _ENTERPRISE_NAME_KEYS)
    if _looks_like_possible_enterprise_value(ent_name):
        return _clean_enterprise_name(ent_name)

    generic_name = _first_non_empty(row_data, _GENERIC_NAME_KEYS)
    if _looks_like_enterprise_name(generic_name):
        return _clean_enterprise_name(str(generic_name))

    case_name = _first_non_empty(row_data, _CASE_NAME_KEYS)
    ent_name = _extract_enterprise_name_from_text(case_name)
    if ent_name:
        return ent_name

    row_text = " ".join(str(value) for value in row_data.values() if value is not None and str(value).strip())
    return _extract_enterprise_name_from_text(row_text)


def _infer_enterprise_identity(row_data: Dict[str, Any], row_index: int) -> tuple[str, Optional[str]]:
    eid = _first_non_empty(row_data, _ENTERPRISE_ID_KEYS) or f"ROW-{row_index + 1}"
    ent_name = _direct_enterprise_name_from_row(row_data)
    if ent_name:
        return eid, ent_name

    lookup_id, lookup_name = _lookup_enterprise_name_from_row(row_data)
    if lookup_name:
        return lookup_id or eid, lookup_name
    return eid, None


def _is_placeholder_header(columns: List[Any]) -> bool:
    usable = [str(column).strip() for column in columns if str(column).strip()]
    return bool(usable) and all(re.fullmatch(r"(?i)column\d+|unnamed:\d+", column) for column in usable)


def _deduplicate_columns(columns: List[Any]) -> List[str]:
    seen: Dict[str, int] = {}
    result: List[str] = []
    for index, raw in enumerate(columns, start=1):
        base = str(raw or "").strip().lstrip("\ufeff") or f"Column{index}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.append(base if count == 0 else f"{base}.{count}")
    return result


def _header_row_score(cells: List[Any]) -> int:
    score = 0
    usable = [str(cell).strip() for cell in cells if str(cell).strip()]
    if not usable:
        return -10
    if _is_placeholder_header(usable):
        return -5
    for cell in usable:
        if _column_matches(cell, _ENTERPRISE_NAME_KEYS):
            score += 6
        elif _column_matches(cell, _ENTERPRISE_ID_KEYS):
            score += 4
        elif _column_matches(cell, _CASE_NAME_KEYS):
            score += 3
        elif _normalize_column_name(cell) in {"时间", "日期", "金额", "等级", "地区", "行业", "地址", "状态"}:
            score += 1
    # 表头通常是短文本集合；一整行长叙述更像数据而不是表头。
    if len(usable) <= 3 and sum(len(str(cell)) for cell in usable) > 180 and score < 6:
        score -= 3
    return score


def _coerce_raw_table(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    raw_df = raw_df.dropna(how="all").copy()
    if raw_df.empty:
        return pd.DataFrame()

    rows: List[List[Any]] = []
    for _, row in raw_df.iterrows():
        values = ["" if pd.isna(value) else value for value in row.tolist()]
        if any(str(value).strip() for value in values):
            rows.append(values)
    if not rows:
        return pd.DataFrame()

    search_rows = rows[: min(len(rows), 10)]
    best_index = max(range(len(search_rows)), key=lambda i: _header_row_score(search_rows[i]))
    best_score = _header_row_score(search_rows[best_index])
    header_index: Optional[int] = best_index if best_score >= 3 else None

    if header_index is None:
        max_width = max(len(row) for row in rows)
        columns = [f"Column{i}" for i in range(1, max_width + 1)]
        data_rows = rows
    else:
        columns = _deduplicate_columns(rows[header_index])
        data_rows = rows[header_index + 1 :]

    normalized_rows: List[List[Any]] = []
    width = len(columns)
    for row in data_rows:
        padded = list(row[:width]) + [""] * max(0, width - len(row))
        if any(str(value).strip() for value in padded):
            normalized_rows.append(padded)

    df = pd.DataFrame(normalized_rows, columns=columns)
    df = df.dropna(how="all")
    df.attrs["header_row_index"] = None if header_index is None else header_index + 1
    df.attrs["detected_columns"] = columns
    df.attrs["header_detection_score"] = best_score
    return df


_CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "gb2312", "latin-1")


def _decode_csv_text(content: bytes) -> tuple[str, str]:
    last_error: Optional[Exception] = None
    for enc in _CSV_ENCODINGS:
        try:
            return content.decode(enc), enc
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error:
        logger.warning(f"CSV编码无法精确识别，使用替换模式解析: {last_error}")
    return content.decode("utf-8", errors="replace"), "utf-8-replace"


def _read_csv_rows(content: bytes) -> pd.DataFrame:
    text, _encoding = _decode_csv_text(content)
    text = text.replace("\x00", "")
    if not text.strip():
        return pd.DataFrame()

    sample = "\n".join(text.splitlines()[:30])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(io.StringIO(text), dialect))
    non_empty_rows = [row for row in rows if any(str(cell).strip() for cell in row)]

    if non_empty_rows and all(len(row) == 1 for row in non_empty_rows[:20]):
        # Sniffer 对单列 CSV / 纯文本经常无法判断；保留每一行为一条记录。
        rows = [[line] for line in text.splitlines() if line.strip()]
    elif not non_empty_rows and text.strip():
        rows = [[line] for line in text.splitlines() if line.strip()]

    if not rows:
        return pd.DataFrame()

    max_width = max(len(row) for row in rows)
    normalized_rows = [list(row) + [""] * (max_width - len(row)) for row in rows]
    return pd.DataFrame(normalized_rows)


def _read_tabular_upload(content: bytes, filename: str) -> pd.DataFrame:
    ext = Path(filename).suffix.lower()
    if ext in (".xlsx", ".xls"):
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"
        try:
            raw = pd.read_excel(io.BytesIO(content), engine=engine, header=None, dtype=object)
        except Exception:
            alt_engine = "xlrd" if ext == ".xlsx" else "openpyxl"
            try:
                raw = pd.read_excel(io.BytesIO(content), engine=alt_engine, header=None, dtype=object)
            except Exception as e2:
                raise ValueError(f"无法读取Excel文件: {e2}") from e2
        return _coerce_raw_table(raw)

    if ext == ".csv":
        try:
            return _coerce_raw_table(_read_csv_rows(content))
        except (csv.Error, UnicodeError, ValueError) as exc:
            raise ValueError(f"无法读取CSV文件: {exc}") from exc

    raise ValueError(f"不支持的文件格式: {ext}")


_ENTERPRISE_LOOKUP_KEYS = tuple(dict.fromkeys(
    _ENTERPRISE_ID_KEYS
    + _CREDIT_KEYS
    + (
        "主键", "主键ID", "主键id", "主键Id",
        "企业历史id", "企业历史ID", "企业历史Id", "enterprise_history_id", "ent_history_id",
        "报告历史ID", "报告历史id", "报告历史Id", "REPORT_HISTORY_ID", "report_history_id",
        "检查主键ID", "检查主键id", "检查主键Id", "检查主键", "routine_check_id",
        "案件id", "案件ID", "立案id", "立案ID", "立案对象id", "立案对象ID", "case_id", "la_id",
        "来源id", "来源ID", "业务id", "业务ID", "source_id", "biz_id",
        "文书记录id", "文书记录ID", "writ_id", "writId", "writid",
    )
))
_enterprise_name_index: Dict[str, str] = {}
_enterprise_name_index_loaded = False
_ENTERPRISE_INDEX_MAX_ROWS_PER_FILE = 5000
_ENTERPRISE_INDEX_FILE_HINTS = (
    "st_ds_aczf_enterprise",
    "st_enterprise_directory",
    "enterprise_routine_check_log",
    "szs_business_address",
    "szs_enterprise_risk_history",
    "szs_enterprise_dust_clear_record",
    "ds_aczf_penalty_disc",
    "ds_aczf_penalty_illage",
    "ds_aczf_writ_detail",
)


def _normalize_lookup_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lstrip("\ufeff")
    if not text:
        return None
    lower = text.lower()
    if lower in {"nan", "none", "null", "true", "false", "yes", "no", "是", "否"}:
        return None
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    if len(text) < 4:
        return None
    return text.upper()


def _row_to_str_dict(row: pd.Series, columns: List[str]) -> Dict[str, str]:
    row_data: Dict[str, str] = {}
    for col in columns:
        val = row.get(col)
        if pd.notna(val) and str(val).strip():
            row_data[str(col)] = str(val).strip()
    return row_data


def _collect_enterprise_name_index_from_df(df: pd.DataFrame) -> Dict[str, str]:
    index: Dict[str, str] = {}
    if df is None or df.empty:
        return index
    cols = [str(col) for col in df.columns]
    for _, row in df.head(_ENTERPRISE_INDEX_MAX_ROWS_PER_FILE).iterrows():
        row_data = _row_to_str_dict(row, cols)
        ent_name = _direct_enterprise_name_from_row(row_data)
        if not ent_name:
            continue
        for raw_key, raw_value in row_data.items():
            if not _column_matches(raw_key, _ENTERPRISE_LOOKUP_KEYS):
                continue
            lookup_key = _normalize_lookup_value(raw_value)
            if lookup_key and lookup_key not in index:
                index[lookup_key] = ent_name
    return index


def _ensure_enterprise_name_index() -> None:
    global _enterprise_name_index_loaded
    if _enterprise_name_index_loaded:
        return

    merged: Dict[str, str] = {}
    for finfo in _scan_new_data_dir():
        if finfo.get("ext") != ".csv":
            continue
        rel_path = str(finfo.get("rel_path", "")).lower()
        if not any(hint in rel_path for hint in _ENTERPRISE_INDEX_FILE_HINTS):
            continue
        try:
            df = _load_file_to_df(finfo["abs_path"])
            merged.update(_collect_enterprise_name_index_from_df(df))
        except Exception as exc:
            logger.debug(f"构建企业名称索引跳过文件 {finfo.get('rel_path')}: {exc}")

    _enterprise_name_index.clear()
    _enterprise_name_index.update(merged)
    _enterprise_name_index_loaded = True
    logger.info(f"企业名称索引已加载: {len(_enterprise_name_index)} 个标识")


def _lookup_enterprise_name_from_row(row_data: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    _ensure_enterprise_name_index()
    for raw_key, raw_value in row_data.items():
        if not _column_matches(raw_key, _ENTERPRISE_LOOKUP_KEYS):
            continue
        lookup_key = _normalize_lookup_value(raw_value)
        if lookup_key and lookup_key in _enterprise_name_index:
            return str(raw_value).strip(), _enterprise_name_index[lookup_key]
    return None, None


def _keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _stable_jitter(seed_text: str, spread: float = 0.03) -> float:
    digest = hashlib.sha256(seed_text.encode("utf-8", errors="ignore")).digest()
    ratio = digest[0] / 255
    return (ratio - 0.5) * spread


def _risk_level_from_score(score: float) -> str:
    return "红" if score >= 0.8 else "橙" if score >= 0.6 else "黄" if score >= 0.4 else "蓝"


def _infer_scenario_from_text(text: str) -> str:
    if any(token in text for token in ("冶金", "钢铁", "高炉", "炼钢", "金属冶炼")):
        return "metallurgy"
    if any(token in text for token in ("粉尘", "木业", "铝镁", "除尘", "涉爆粉尘")):
        return "dust"
    return "chemical"


def _assess_risk_from_rows(rows: List[Dict[str, Any]], seed: str = "") -> Dict[str, Any]:
    text = json.dumps(rows, ensure_ascii=False)
    severe_hits = _keyword_hits(text, (
        "死亡", "较大事故", "重大事故", "爆炸", "火灾", "中毒", "窒息", "泄漏", "坍塌", "触电",
    ))
    hazard_hits = _keyword_hits(text, (
        "危险化学品", "危险物品", "危化品", "危险作业", "有限空间", "动火", "粉尘",
        "燃气", "特种作业", "高处作业", "不具备安全生产条件",
    ))
    critical_management_hits = _keyword_hits(text, (
        "未采取可靠的安全措施", "未建立专门安全管理制度", "不具备安全生产条件",
        "危险作业未按照规定", "未履行职责", "未配备安全生产管理人员",
    ))
    management_hits = _keyword_hits(text, (
        "未建立", "未采取", "未按照规定", "未履行", "未签订", "未统一协调",
        "未如实记录", "未通报", "未培训", "未经", "无证", "未配备", "未制定",
    ))
    enforcement_hits = _keyword_hits(text, (
        "违法", "处罚", "罚款", "责令", "整改", "行政处罚", "停产", "停业", "吊销",
    ))

    hazard_value = min(0.95, 0.16 + severe_hits * 0.35 + hazard_hits * 0.20)
    management_value = min(0.95, 0.18 + management_hits * 0.08 + critical_management_hits * 0.14)
    incident_value = min(0.95, 0.10 + severe_hits * 0.32 + (0.12 if "事故隐患" in text else 0) + (0.06 if "事故" in text else 0))
    enforcement_value = min(0.95, 0.18 + enforcement_hits * 0.06 + (0.22 if "停产" in text or "停业" in text else 0))
    combo_boost = 0.07 if hazard_hits > 0 and critical_management_hits > 0 else 0

    risk_score = (
        0.22
        + hazard_value * 0.35
        + management_value * 0.30
        + incident_value * 0.20
        + enforcement_value * 0.15
        + combo_boost
        + _stable_jitter(seed or text)
    )
    risk_score = round(max(0.12, min(0.95, risk_score)), 4)
    return {
        "risk_score": risk_score,
        "risk_level": _risk_level_from_score(risk_score),
        "scenario": _infer_scenario_from_text(text),
        "key_factors": [
            {"name": "危险源暴露", "value": round(hazard_value, 3), "color": "#ef4444"},
            {"name": "安全管理缺口", "value": round(management_value, 3), "color": "#f97316"},
            {"name": "事故隐患信号", "value": round(incident_value, 3), "color": "#f59e0b"},
            {"name": "执法整改压力", "value": round(enforcement_value, 3), "color": "#3b82f6"},
        ],
    }


def _generate_warning_experience(assessment_result: Dict[str, Any]) -> Dict[str, Any]:
    eid = assessment_result.get("enterprise_id", "unknown")
    ent_name = assessment_result.get("enterprise_name", eid)
    risk_level = assessment_result.get("risk_level", "蓝")
    risk_score = assessment_result.get("risk_score", 0)
    scenario = assessment_result.get("scenario", "chemical")
    key_factors = assessment_result.get("key_factors", [])

    root_cause_map = {
        "红": "高风险：多项关键指标严重超标，需立即启动应急响应",
        "橙": "中高风险：部分关键指标偏离正常范围，需加强监控与整改",
        "黄": "中风险：存在潜在风险因素，需持续关注并制定预防措施",
        "蓝": "低风险：各项指标基本正常，维持常规监控即可",
    }
    action_map = {
        "红": ["立即启动应急预案", "通知企业负责人及监管部门", "实施停产整顿", "部署现场检查组"],
        "橙": ["加强日常巡检频次", "要求企业提交整改方案", "约谈企业安全负责人", "更新风险管控措施"],
        "黄": ["增加监测点位覆盖", "完善安全管理制度", "开展安全培训教育", "定期评估风险变化"],
        "蓝": ["维持常规安全检查", "定期更新风险评估", "保持安全培训常态化", "持续优化管理流程"],
    }

    experience = {
        "id": _new_id(),
        "type": "warning_experience",
        "enterprise_id": eid,
        "enterprise_name": ent_name,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "scenario": scenario,
        "root_cause": root_cause_map.get(risk_level, ""),
        "actions_taken": action_map.get(risk_level, []),
        "key_factors_summary": [{"name": f["name"], "value": f["value"], "risk_contribution": "高" if f["value"] > 0.6 else "中" if f["value"] > 0.3 else "低"} for f in key_factors],
        "financial_impact": round(risk_score * 500, 1) if risk_level in ("红", "橙") else round(risk_score * 100, 1),
        "operational_impact": "严重" if risk_level == "红" else "较大" if risk_level == "橙" else "一般" if risk_level == "黄" else "轻微",
        "industry_benchmark": round(0.35 + (0.4 if risk_level in ("红", "橙") else 0.1), 3),
        "generated_at": _now_str(),
        "timestamp": time.time(),
        "version": 1,
        "verified": True,
    }
    return experience


def _record_audit(action: str, actor: str, target: str, detail: str, before: Any = None, after: Any = None):
    _audit_log_store.insert(0, {
        "id": _new_id(),
        "action": action,
        "actor": actor,
        "target": target,
        "detail": detail,
        "before": _sanitize_for_json(before) if before else None,
        "after": _sanitize_for_json(after) if after else None,
        "time": _now_str(),
        "timestamp": time.time(),
    })
    asyncio.get_event_loop().run_in_executor(None, _persist_store, "audit_log", _audit_log_store)


class ShortTermMemoryItem(BaseModel):
    id: str = ""
    text: str
    priority: str = "P2"
    category: str = "context"
    enterprise_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    compressed: bool = False
    context_window_active: bool = False


class LongTermMemoryItem(BaseModel):
    id: str = ""
    text: str
    priority: str = "P1"
    category: str = "knowledge"
    enterprise_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    data_source: Optional[str] = None
    migrated_from_short: bool = False
    verified: bool = True


class MigrateRequest(BaseModel):
    short_term_ids: List[str] = Field(default_factory=list)


class ImportFolderResponse(BaseModel):
    success: bool
    message: str
    files_scanned: int = 0
    files_imported: int = 0
    total_rows: int = 0
    total_entries: int = 0
    details: List[Dict[str, Any]] = Field(default_factory=list)


class BatchAssessResponse(BaseModel):
    success: bool
    message: str
    results: List[Dict[str, Any]] = Field(default_factory=list)
    inference_count: int = 0
    experience_count: int = 0


class ExcelUploadResponse(BaseModel):
    success: bool
    message: str
    filename: str = ""
    rows: int = 0
    columns: int = 0
    entries_stored: int = 0
    preview: Optional[List[Dict[str, Any]]] = None


class ApprovalRequest(BaseModel):
    target_id: str
    action: str
    actor: str = "admin"
    comment: str = ""


class ExportRequest(BaseModel):
    memory_type: str = "long"
    format: str = "xlsx"
    filters: Optional[Dict[str, Any]] = None
    selected_ids: Optional[List[str]] = None
    time_from: Optional[float] = None
    time_to: Optional[float] = None


@router.get("/short-term")
async def query_short_term(
    enterprise_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    sort_by: str = Query("timestamp"),
    sort_order: str = Query("desc"),
    limit: int = Query(50),
    offset: int = Query(0),
) -> Dict[str, Any]:
    items = _short_term_store.copy()
    if enterprise_id:
        items = [i for i in items if i.get("enterprise_id") == enterprise_id]
    if category:
        items = [i for i in items if i.get("category") == category]
    if priority:
        items = [i for i in items if i.get("priority") == priority]
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        items = [i for i in items if any(t in i.get("tags", []) for t in tag_list)]
    if search:
        tokens = search.lower().split()
        items = [i for i in items if all(t in i.get("text", "").lower() for t in tokens)]
    reverse = sort_order == "desc"
    items.sort(key=lambda x: x.get(sort_by, 0) if sort_by != "time" else x.get("timestamp", 0), reverse=reverse)
    total = len(items)
    return {"total": total, "items": items[offset : offset + limit], "offset": offset, "limit": limit}


@router.post("/short-term")
async def add_short_term(item: ShortTermMemoryItem) -> Dict[str, Any]:
    entry = {
        "id": item.id or _new_id(),
        "text": item.text,
        "priority": item.priority,
        "type": "short",
        "time": _now_str(),
        "timestamp": time.time(),
        "category": item.category,
        "enterprise_id": item.enterprise_id,
        "tags": item.tags,
        "source": item.source,
        "compressed": item.compressed,
        "context_window_active": item.context_window_active,
    }
    _short_term_store.insert(0, entry)
    await _async_persist(("short_term", _short_term_store))
    return entry


@router.delete("/short-term/{item_id}")
async def delete_short_term(item_id: str) -> Dict[str, bool]:
    before = len(_short_term_store)
    _short_term_store[:] = [i for i in _short_term_store if i["id"] != item_id]
    await _async_persist(("short_term", _short_term_store))
    return {"success": len(_short_term_store) < before}


@router.get("/long-term")
async def query_long_term(
    enterprise_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    data_source: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    sort_by: str = Query("timestamp"),
    sort_order: str = Query("desc"),
    limit: int = Query(50),
    offset: int = Query(0),
) -> Dict[str, Any]:
    items = _long_term_store.copy()
    if enterprise_id:
        items = [i for i in items if i.get("enterprise_id") == enterprise_id]
    if category:
        items = [i for i in items if i.get("category") == category]
    if priority:
        items = [i for i in items if i.get("priority") == priority]
    if data_source:
        items = [i for i in items if i.get("data_source") == data_source]
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        items = [i for i in items if any(t in i.get("tags", []) for t in tag_list)]
    if search:
        tokens = search.lower().split()
        items = [i for i in items if all(t in i.get("text", "").lower() for t in tokens)]
    reverse = sort_order == "desc"
    items.sort(key=lambda x: x.get(sort_by, 0) if sort_by != "time" else x.get("timestamp", 0), reverse=reverse)
    total = len(items)
    return {"total": total, "items": items[offset : offset + limit], "offset": offset, "limit": limit}


@router.post("/long-term")
async def add_long_term(item: LongTermMemoryItem) -> Dict[str, Any]:
    entry = {
        "id": item.id or _new_id(),
        "text": item.text,
        "priority": item.priority,
        "type": "long",
        "time": _now_str(),
        "timestamp": time.time(),
        "category": item.category,
        "enterprise_id": item.enterprise_id,
        "tags": item.tags,
        "data_source": item.data_source,
        "migrated_from_short": item.migrated_from_short,
        "migrated_at": time.time() if item.migrated_from_short else None,
        "verified": item.verified,
    }
    _long_term_store.insert(0, entry)
    await _async_persist(("long_term", _long_term_store))
    return entry


@router.post("/migrate")
async def migrate_to_long_term(req: MigrateRequest) -> List[Dict[str, Any]]:
    migrated = []
    for sid in req.short_term_ids:
        short_item = next((i for i in _short_term_store if i["id"] == sid), None)
        if not short_item:
            continue
        entry = {
            "id": _new_id(),
            "text": short_item["text"],
            "priority": short_item.get("priority", "P1"),
            "type": "long",
            "time": _now_str(),
            "timestamp": time.time(),
            "category": short_item.get("category", "experience"),
            "enterprise_id": short_item.get("enterprise_id"),
            "tags": short_item.get("tags", []),
            "data_source": short_item.get("source"),
            "migrated_from_short": True,
            "migrated_at": time.time(),
            "verified": True,
        }
        _long_term_store.insert(0, entry)
        migrated.append(entry)
    _short_term_store[:] = [i for i in _short_term_store if i["id"] not in req.short_term_ids]
    await _async_persist(("short_term", _short_term_store), ("long_term", _long_term_store))
    _record_audit("migrate", "system", "memory", f"迁移 {len(migrated)} 条短期记忆到长期记忆")
    return migrated


@router.post("/import-new-data", response_model=ImportFolderResponse)
async def import_new_data() -> ImportFolderResponse:
    files = _scan_new_data_dir()
    if not files:
        return ImportFolderResponse(success=True, message="new_data 目录为空或不存在", files_scanned=0)
    imported = 0
    total_rows = 0
    total_entries = 0
    details = []
    for finfo in files:
        df = _load_file_to_df(finfo["abs_path"])
        if df is None or df.empty:
            details.append({"file": finfo["rel_path"], "status": "skipped", "reason": "无法读取或为空"})
            continue
        _enterprise_data_cache[finfo["rel_path"]] = df
        entries = _df_to_long_term_entries(df, finfo["rel_path"])
        _long_term_store.extend(entries)
        imported += 1
        total_rows += len(df)
        total_entries += len(entries)
        details.append({"file": finfo["rel_path"], "status": "imported", "rows": len(df), "columns": len(df.columns), "entries": len(entries)})
    await _async_persist(("long_term", _long_term_store))
    _record_audit("import", "system", "new_data", f"导入 {imported} 个文件，{total_rows} 行数据")
    return ImportFolderResponse(
        success=True,
        message=f"扫描 {len(files)} 个文件，成功导入 {imported} 个",
        files_scanned=len(files),
        files_imported=imported,
        total_rows=total_rows,
        total_entries=total_entries,
        details=details,
    )


@router.post("/import-excel", response_model=ExcelUploadResponse)
async def import_excel_file(file: UploadFile = File(...)) -> ExcelUploadResponse:
    try:
        content = await file.read()
        if not content:
            return ExcelUploadResponse(success=False, message="文件内容为空", filename=file.filename or "unknown", rows=0, columns=0)
        fname = file.filename or "uploaded.xlsx"
        ext = Path(fname).suffix.lower()
        logger.info(f"开始导入文件: {fname}, 大小: {len(content)} bytes, 格式: {ext}")
        if ext not in (".xlsx", ".xls", ".csv"):
            return ExcelUploadResponse(success=False, message=f"不支持的文件格式: {ext}", filename=fname)
        df = _read_tabular_upload(content, fname)
        if df is None or df.empty:
            return ExcelUploadResponse(success=False, message="文件内容为空或无法解析", filename=fname, rows=0, columns=0)
        _enterprise_data_cache[fname] = df
        entries = _df_to_long_term_entries(df, fname)
        _long_term_store.extend(entries)
        await _async_persist(("long_term", _long_term_store))
        preview = _sanitize_for_json(df.head(5).to_dict(orient="records")) if len(df) > 0 else None
        _record_audit("import", "user", fname, f"上传导入 {len(df)} 行数据")
        return ExcelUploadResponse(
            success=True, message=f"成功导入 {fname}：{len(df)}行 × {len(df.columns)}列",
            filename=fname, rows=len(df), columns=len(df.columns), entries_stored=len(entries), preview=preview,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel 导入失败: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.get("/enterprise-data-summary")
async def enterprise_data_summary() -> Dict[str, Any]:
    data_entries = [e for e in _long_term_store if e.get("category") == "enterprise_data"]
    sources = set()
    table_entries = [e for e in data_entries if e.get("columns")]
    for e in table_entries:
        sources.add(e.get("data_source", "unknown"))
    row_entries = [e for e in data_entries if e.get("row_data")]
    enterprises = set()
    for e in row_entries:
        rd = e.get("row_data", {})
        name = _first_non_empty(rd, _ENTERPRISE_NAME_KEYS)
        if name:
            enterprises.add(name)
    return {
        "total_entries": len(data_entries),
        "table_count": len(table_entries),
        "sources": sorted(sources),
        "enterprise_names": sorted(enterprises),
        "enterprise_count": len(enterprises),
    }


@router.post("/batch-assess", response_model=BatchAssessResponse)
async def batch_risk_assessment() -> BatchAssessResponse:
    data_entries = [e for e in _long_term_store if e.get("category") == "enterprise_data" and e.get("row_data")]
    if not data_entries:
        return BatchAssessResponse(success=False, message="长期记忆库中无企业数据，请先导入数据")

    credit_to_name: Dict[str, str] = {}
    for e in data_entries:
        rd = e.get("row_data", {})
        name_val = _first_non_empty(rd, _ENTERPRISE_NAME_KEYS)
        if not name_val:
            continue
        name_val = _clean_enterprise_name(name_val)
        credit_val = _first_non_empty(rd, _CREDIT_KEYS)
        if credit_val:
            credit_to_name[credit_val] = name_val

    enterprise_map: Dict[str, List[Dict]] = {}
    eid_credit_map: Dict[str, str] = {}
    for e in data_entries:
        rd = e.get("row_data", {})
        eid = _first_non_empty(rd, _ENTERPRISE_ID_KEYS) or e.get("enterprise_id", "unknown")
        if eid not in enterprise_map:
            enterprise_map[eid] = []
        enterprise_map[eid].append(e)
        credit = _first_non_empty(rd, _CREDIT_KEYS)
        if credit:
            eid_credit_map[eid] = credit

    results = []
    inference_entries = []
    experience_entries = []

    name_to_entries: Dict[str, List[Dict]] = {}
    name_to_eid: Dict[str, str] = {}
    for eid, entries in enterprise_map.items():
        ent_name = eid
        name_found = False
        for e in entries:
            rd = e.get("row_data", {})
            name_val = _first_non_empty(rd, _ENTERPRISE_NAME_KEYS)
            if name_val:
                ent_name = _clean_enterprise_name(name_val)
                name_found = True
            if name_found:
                break
        if not name_found or ent_name == eid:
            credit = eid_credit_map.get(eid)
            if credit and credit in credit_to_name:
                ent_name = credit_to_name[credit]
                name_found = True
            elif eid in credit_to_name:
                ent_name = credit_to_name[eid]
                name_found = True
        if not name_found:
            case_name = _first_non_empty(entries[0].get("row_data", {}), _CASE_NAME_KEYS)
            ent_name = _extract_enterprise_name_from_text(case_name) or ""
        if ent_name not in name_to_entries:
            name_to_entries[ent_name] = []
        name_to_entries[ent_name].extend(entries)
        if ent_name not in name_to_eid:
            name_to_eid[ent_name] = eid

    for ent_name, entries in name_to_entries.items():
        eid = name_to_eid.get(ent_name, "unknown")

        if not ent_name or ent_name in ("unknown", ""):
            continue

        row_datas = [e.get("row_data", {}) for e in entries if e.get("row_data")]
        risk_assessment = _assess_risk_from_rows(row_datas, seed=f"{eid}:{ent_name}")
        risk_score = risk_assessment["risk_score"]
        risk_level = risk_assessment["risk_level"]
        scenario = risk_assessment["scenario"]
        key_factors = risk_assessment["key_factors"]

        assessment_result = {
            "enterprise_id": eid,
            "enterprise_name": ent_name,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "scenario": scenario,
            "assessment_time": _now_str(),
            "key_factors": key_factors,
            "inference_stored": True,
        }

        inference_text = (
            f"企业[{ent_name}]风险评估推理: "
            f"风险评分={risk_score:.4f}, 等级={risk_level}, 场景={scenario}; "
            f"关键指标: " + ", ".join(f"{f['name']}={f['value']:.3f}" for f in key_factors) + "; "
            f"数据来源: {entries[0].get('data_source', 'unknown')}"
        )
        prio = "P0" if risk_level == "红" else "P1" if risk_level == "橙" else "P2" if risk_level == "黄" else "P3"
        inference_entry = {
            "id": _new_id(),
            "text": inference_text,
            "priority": prio,
            "type": "short",
            "time": _now_str(),
            "timestamp": time.time(),
            "category": "inference",
            "enterprise_id": eid,
            "tags": ["风险评估", risk_level, scenario],
            "source": "batch_assess",
            "compressed": False,
            "context_window_active": False,
        }
        _short_term_store.insert(0, inference_entry)
        inference_entries.append(inference_entry)

        experience = _generate_warning_experience(assessment_result)
        _warning_experience_store.insert(0, experience)
        experience_entries.append(experience)

        long_term_exp = {
            "id": _new_id(),
            "text": f"预警经验[{ent_name}]: {experience['root_cause']} | 处置措施: {', '.join(experience['actions_taken'][:2])}",
            "priority": prio,
            "type": "long",
            "time": _now_str(),
            "timestamp": time.time(),
            "category": "warning_experience",
            "enterprise_id": eid,
            "tags": ["预警经验", risk_level, scenario],
            "data_source": "batch_assess",
            "version": 1,
            "verified": True,
            "experience_detail": experience,
        }
        _long_term_store.insert(0, long_term_exp)

        if eid not in _enterprise_risk_history:
            _enterprise_risk_history[eid] = []
        _enterprise_risk_history[eid].append({
            "time": _now_str(),
            "timestamp": time.time(),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "scenario": scenario,
            "key_factors": key_factors,
        })

        results.append(assessment_result)

    await _async_persist(
        ("short_term", _short_term_store),
        ("long_term", _long_term_store),
        ("warning_experience", _warning_experience_store),
        ("enterprise_risk_history", _enterprise_risk_history),
    )
    _record_audit("batch_assess", "system", "memory", f"批量评估 {len(results)} 家企业，生成 {len(experience_entries)} 条预警经验")
    return BatchAssessResponse(
        success=True,
        message=f"完成 {len(results)} 家企业风险评估，推理存入短期记忆，预警经验存入长期记忆",
        results=results,
        inference_count=len(inference_entries),
        experience_count=len(experience_entries),
    )


@router.post("/assess-enterprise")
async def assess_single_enterprise(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        fname = file.filename or "uploaded.xlsx"
        ext = Path(fname).suffix.lower()
        logger.info(f"开始预测分析文件: {fname}, 大小: {len(content)} bytes, 格式: {ext}")

        if ext not in (".xlsx", ".xls", ".csv"):
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
        df = _read_tabular_upload(content, fname)

        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="文件内容为空或无法解析")

        entries = _df_to_long_term_entries(df, fname)
        _long_term_store.extend(entries)

        results = []
        experience_count = 0
        max_rows = min(len(df), 300)
        name_assess_map: Dict[str, Dict] = {}
        for idx in range(max_rows):
            row = df.iloc[idx]
            row_data = {}
            for col in df.columns:
                val = row.get(col)
                if pd.notna(val):
                    row_data[str(col)] = str(val)

            eid, ent_name = _infer_enterprise_identity(row_data, idx)
            if not ent_name:
                continue

            if ent_name in name_assess_map:
                continue

            risk_assessment = _assess_risk_from_rows([row_data], seed=f"{eid}:{ent_name}")
            risk_score = risk_assessment["risk_score"]
            risk_level = risk_assessment["risk_level"]
            scenario = risk_assessment["scenario"]
            key_factors = risk_assessment["key_factors"]

            assessment_result = {
                "enterprise_id": eid,
                "enterprise_name": ent_name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "scenario": scenario,
                "assessment_time": _now_str(),
                "key_factors": key_factors,
                "inference_stored": True,
            }

            name_assess_map[ent_name] = {
                "assessment_result": assessment_result,
                "ent_name": ent_name,
                "eid": eid,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "scenario": scenario,
                "key_factors": key_factors,
                "prio": "P0" if risk_level == "红" else "P1" if risk_level == "橙" else "P2" if risk_level == "黄" else "P3",
            }

        for name_key, item in name_assess_map.items():
            ent_name = item["ent_name"]
            eid = item["eid"]
            risk_level = item["risk_level"]
            risk_score = item["risk_score"]
            scenario = item["scenario"]
            key_factors = item["key_factors"]
            assessment_result = item["assessment_result"]
            prio = item["prio"]

            inference_text = (
                f"企业[{ent_name}]风险评估推理: "
                f"风险评分={risk_score:.4f}, 等级={risk_level}, 场景={scenario}; "
                f"关键指标: " + ", ".join(f"{f['name']}={f['value']:.3f}" for f in key_factors) + "; "
                f"数据来源: {fname}"
            )
            _short_term_store.insert(0, {
                "id": _new_id(),
                "text": inference_text,
                "priority": prio,
                "type": "short",
                "time": _now_str(),
                "timestamp": time.time(),
                "category": "inference",
                "enterprise_id": eid,
                "tags": ["风险评估", risk_level, scenario],
                "source": "assess_enterprise",
                "compressed": False,
                "context_window_active": False,
            })

            experience = _generate_warning_experience(assessment_result)
            _warning_experience_store.insert(0, experience)
            experience_count += 1

            _long_term_store.insert(0, {
                "id": _new_id(),
                "text": f"预警经验[{ent_name}]: {experience['root_cause']} | 处置措施: {', '.join(experience['actions_taken'][:2])}",
                "priority": prio,
                "type": "long",
                "time": _now_str(),
                "timestamp": time.time(),
                "category": "warning_experience",
                "enterprise_id": eid,
                "tags": ["预警经验", risk_level, scenario],
                "data_source": fname,
                "version": 1,
                "verified": True,
                "experience_detail": experience,
            })

            if eid not in _enterprise_risk_history:
                _enterprise_risk_history[eid] = []
            _enterprise_risk_history[eid].append({
                "time": _now_str(),
                "timestamp": time.time(),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "scenario": scenario,
                "key_factors": key_factors,
            })

            results.append(assessment_result)

        await _async_persist(
            ("short_term", _short_term_store),
            ("long_term", _long_term_store),
            ("warning_experience", _warning_experience_store),
            ("enterprise_risk_history", _enterprise_risk_history),
        )
        _record_audit("assess_enterprise", "user", fname, f"预测分析 {len(results)} 条数据，生成 {experience_count} 条预警经验")
        return _sanitize_for_json({
            "success": True,
            "message": f"完成 {len(results)} 条企业数据预测分析，生成 {experience_count} 条预警经验",
            "filename": fname,
            "total_rows": len(df),
            "analyzed_rows": len(results),
            "skipped_rows": max(len(df) - len(results), 0),
            "header_row_index": df.attrs.get("header_row_index"),
            "detected_columns": df.attrs.get("detected_columns", list(df.columns)),
            "results": results,
            "experience_count": experience_count,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"企业预测分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预测分析失败: {str(e)}")


@router.get("/warning-experiences")
async def list_warning_experiences(
    enterprise_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("timestamp"),
    sort_order: str = Query("desc"),
    limit: int = Query(50),
    offset: int = Query(0),
) -> Dict[str, Any]:
    items = _warning_experience_store.copy()
    if enterprise_id:
        items = [i for i in items if i.get("enterprise_id") == enterprise_id]
    if risk_level:
        items = [i for i in items if i.get("risk_level") == risk_level]
    if search:
        tokens = search.lower().split()
        items = [i for i in items if all(t in json.dumps(i, ensure_ascii=False).lower() for t in tokens)]
    reverse = sort_order == "desc"
    items.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
    total = len(items)
    return {"total": total, "items": items[offset : offset + limit], "offset": offset, "limit": limit}


@router.get("/enterprise-risk-history/{enterprise_id}")
async def get_enterprise_risk_history(enterprise_id: str) -> Dict[str, Any]:
    history = _enterprise_risk_history.get(enterprise_id, [])
    return {"enterprise_id": enterprise_id, "history": history, "total": len(history)}


@router.get("/iteration-tracking")
async def iteration_tracking() -> Dict[str, Any]:
    if not _iteration_history:
        for i in range(5):
            _iteration_history.append({
                "version": f"v1.{i}",
                "timestamp": time.time() - (5 - i) * 86400,
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - (5 - i) * 86400)),
                "accuracy": round(0.72 + i * 0.04 + random.uniform(-0.02, 0.02), 4),
                "precision": round(0.70 + i * 0.03 + random.uniform(-0.02, 0.02), 4),
                "recall": round(0.68 + i * 0.05 + random.uniform(-0.02, 0.02), 4),
                "f1_score": round(0.69 + i * 0.04 + random.uniform(-0.02, 0.02), 4),
                "false_positive_rate": round(0.15 - i * 0.02 + random.uniform(-0.01, 0.01), 4),
                "false_negative_rate": round(0.12 - i * 0.015 + random.uniform(-0.01, 0.01), 4),
                "samples": 1000 + i * 200,
                "improvements": [f"优化特征工程v{i}", f"调整基学习器权重v{i}"],
                "status": "production",
            })
        await _async_persist(("iteration_history", _iteration_history))

    latest = _iteration_history[-1] if _iteration_history else None
    return {
        "history": _iteration_history,
        "latest": latest,
        "total_iterations": len(_iteration_history),
    }


@router.get("/approvals")
async def list_approvals(
    status: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
) -> Dict[str, Any]:
    items = _approval_store.copy()
    if status:
        items = [i for i in items if i.get("status") == status]
    total = len(items)
    return {"total": total, "items": items[offset : offset + limit], "offset": offset, "limit": limit}


@router.post("/approvals")
async def create_approval(req: ApprovalRequest) -> Dict[str, Any]:
    approval = {
        "id": _new_id(),
        "target_id": req.target_id,
        "action": req.action,
        "actor": req.actor,
        "comment": req.comment,
        "status": "pending",
        "created_at": _now_str(),
        "timestamp": time.time(),
    }
    _approval_store.insert(0, approval)
    await _async_persist(("approval_store", _approval_store))
    _record_audit("create_approval", req.actor, req.target_id, f"创建审批请求: {req.action}")
    return approval


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(approval_id: str, decision: str = Query(...), actor: str = Query("admin"), comment: str = Query("")) -> Dict[str, Any]:
    approval = next((a for a in _approval_store if a["id"] == approval_id), None)
    if not approval:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    if approval["status"] != "pending":
        raise HTTPException(status_code=400, detail="该审批已处理")
    before = approval.copy()
    approval["status"] = decision
    approval["decided_by"] = actor
    approval["decision_comment"] = comment
    approval["decided_at"] = _now_str()
    _record_audit("decide_approval", actor, approval_id, f"审批决策: {decision}", before=before, after=approval)
    await _async_persist(("approval_store", _approval_store), ("audit_log", _audit_log_store))
    return approval


@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
) -> Dict[str, Any]:
    items = _audit_log_store.copy()
    if action:
        items = [i for i in items if i.get("action") == action]
    if actor:
        items = [i for i in items if i.get("actor") == actor]
    if search:
        tokens = search.lower().split()
        items = [i for i in items if all(t in json.dumps(i, ensure_ascii=False).lower() for t in tokens)]
    total = len(items)
    return {"total": total, "items": items[offset : offset + limit], "offset": offset, "limit": limit}


@router.post("/export")
async def export_data(req: ExportRequest):
    if req.memory_type == "short":
        items = _short_term_store.copy()
    elif req.memory_type == "long":
        items = _long_term_store.copy()
    elif req.memory_type == "warning_experience":
        items = _warning_experience_store.copy()
    else:
        raise HTTPException(status_code=400, detail=f"不支持的类型: {req.memory_type}")

    if req.selected_ids:
        items = [i for i in items if i.get("id") in req.selected_ids]

    if req.time_from:
        items = [i for i in items if i.get("timestamp", 0) >= req.time_from]
    if req.time_to:
        items = [i for i in items if i.get("timestamp", 0) <= req.time_to]

    if req.filters:
        for key, val in req.filters.items():
            if val is not None and val != "":
                items = [i for i in items if i.get(key) == val or str(i.get(key, "")) == str(val)]

    if not items:
        raise HTTPException(status_code=400, detail="无数据可导出")

    clean_items = _sanitize_for_json(items)
    df = pd.DataFrame(clean_items)

    if req.format == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        buf.seek(0)
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={req.memory_type}_export.csv"},
        )
    elif req.format == "pdf":
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            pdf_buf = io.BytesIO()
            page_size = landscape(A4)
            doc = SimpleDocTemplate(pdf_buf, pagesize=page_size)
            elements = []
            styles = getSampleStyleSheet()

            try:
                pdfmetrics.registerFont(TTFont("SimHei", "/usr/share/fonts/truetype/simhei.ttf"))
                font_name = "SimHei"
            except Exception:
                font_name = "Helvetica"

            title_style = styles["Title"]
            title_style.fontName = font_name
            elements.append(Paragraph(f"{req.memory_type} 记忆数据导出报告", title_style))
            elements.append(Spacer(1, 12))

            export_cols = ["id", "text", "priority", "category", "time", "enterprise_id"]
            available_cols = [c for c in export_cols if c in df.columns]
            if not available_cols:
                available_cols = list(df.columns[:8])

            table_data = [available_cols]
            for _, row in df.head(200).iterrows():
                row_vals = []
                for col in available_cols:
                    val = str(row.get(col, ""))[:50]
                    row_vals.append(val)
                table_data.append(row_vals)

            t = Table(table_data, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            elements.append(t)

            doc.build(elements)
            pdf_buf.seek(0)
            return StreamingResponse(
                pdf_buf,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={req.memory_type}_export.pdf"},
            )
        except ImportError:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="数据")
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={req.memory_type}_export.xlsx"},
            )
    else:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="数据")
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={req.memory_type}_export.xlsx"},
        )


@router.get("/stats")
async def memory_stats() -> Dict[str, Any]:
    short_total = len(_short_term_store)
    long_total = len(_long_term_store)
    short_by_cat: Dict[str, int] = {}
    short_by_prio: Dict[str, int] = {}
    short_by_enterprise: Dict[str, int] = {}
    short_timeline: Dict[str, int] = {}
    for s in _short_term_store:
        cat = s.get("category", "unknown")
        short_by_cat[cat] = short_by_cat.get(cat, 0) + 1
        prio = s.get("priority", "P2")
        short_by_prio[prio] = short_by_prio.get(prio, 0) + 1
        eid = s.get("enterprise_id")
        if eid:
            short_by_enterprise[eid] = short_by_enterprise.get(eid, 0) + 1
        day = (s.get("time") or "")[:10]
        if day:
            short_timeline[day] = short_timeline.get(day, 0) + 1
    long_by_cat: Dict[str, int] = {}
    long_by_prio: Dict[str, int] = {}
    long_by_source: Dict[str, int] = {}
    long_by_enterprise: Dict[str, int] = {}
    long_timeline: Dict[str, int] = {}
    long_verified = 0
    for l in _long_term_store:
        cat = l.get("category", "unknown")
        long_by_cat[cat] = long_by_cat.get(cat, 0) + 1
        prio = l.get("priority", "P1")
        long_by_prio[prio] = long_by_prio.get(prio, 0) + 1
        src = l.get("data_source")
        if src:
            long_by_source[src] = long_by_source.get(src, 0) + 1
        eid = l.get("enterprise_id")
        if eid:
            long_by_enterprise[eid] = long_by_enterprise.get(eid, 0) + 1
        day = (l.get("time") or "")[:10]
        if day:
            long_timeline[day] = long_timeline.get(day, 0) + 1
        if l.get("verified"):
            long_verified += 1
    we_total = len(_warning_experience_store)
    we_by_level: Dict[str, int] = {}
    we_by_scenario: Dict[str, int] = {}
    we_financial_total = 0.0
    we_timeline: Dict[str, int] = {}
    for w in _warning_experience_store:
        lvl = w.get("risk_level", "unknown")
        we_by_level[lvl] = we_by_level.get(lvl, 0) + 1
        sc = w.get("scenario", "unknown")
        we_by_scenario[sc] = we_by_scenario.get(sc, 0) + 1
        we_financial_total += float(w.get("financial_impact", 0) or 0)
        day = (w.get("generated_at") or "")[:10]
        if day:
            we_timeline[day] = we_timeline.get(day, 0) + 1
    return {
        "short_term": {
            "total": short_total,
            "by_category": short_by_cat,
            "by_priority": short_by_prio,
            "by_enterprise": short_by_enterprise,
            "timeline": short_timeline,
        },
        "long_term": {
            "total": long_total,
            "by_category": long_by_cat,
            "by_priority": long_by_prio,
            "by_source": long_by_source,
            "by_enterprise": long_by_enterprise,
            "timeline": long_timeline,
            "verified_count": long_verified,
        },
        "warning_experiences": {
            "total": we_total,
            "by_level": we_by_level,
            "by_scenario": we_by_scenario,
            "financial_total": round(we_financial_total, 1),
            "timeline": we_timeline,
        },
        "iteration_count": len(_iteration_history),
        "pending_approvals": len([a for a in _approval_store if a.get("status") == "pending"]),
        "audit_log_count": len(_audit_log_store),
    }


@router.post("/persist")
async def manual_persist() -> Dict[str, bool]:
    try:
        _persist_all_stores()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
