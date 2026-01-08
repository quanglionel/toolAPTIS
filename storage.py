# -*- coding: utf-8 -*-
"""
Module lưu trữ dữ liệu - Hỗ trợ cả local JSON và Supabase cloud
Sử dụng REST API trực tiếp thay vì SDK để tránh vấn đề dependency
"""
import json
import os
import streamlit as st
import requests

# File lưu dữ liệu local (fallback)
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "question_bank.json")

# Default empty question bank
DEFAULT_BANK = {
    1: [],  # Nhóm 1: MCQ đơn (Q1-13)
    2: [],  # Nhóm 2: ORDER (Q14)
    3: [],  # Nhóm 3: GENDER BLOCK (Q15)
    4: [],  # Nhóm 4: MCQ multi (Q16-17)
}


def _get_supabase_config():
    """Lấy Supabase config nếu có"""
    try:
        if "supabase" in st.secrets:
            return {
                "url": st.secrets["supabase"]["url"],
                "key": st.secrets["supabase"]["key"]
            }
    except Exception:
        pass
    return None


def _convert_keys_to_str(data: dict) -> dict:
    """Chuyển key từ int sang string để lưu JSON"""
    return {str(k): v for k, v in data.items()}


def _convert_keys_to_int(data: dict) -> dict:
    """Chuyển key từ string sang int khi đọc"""
    result = {}
    for key in ["1", "2", "3", "4"]:
        int_key = int(key)
        result[int_key] = data.get(key, data.get(int_key, []))
    return result


# ========== SUPABASE REST API FUNCTIONS ==========

def _save_to_supabase(config, question_bank: dict) -> bool:
    """Lưu dữ liệu lên Supabase qua REST API"""
    try:
        data_str = json.dumps(_convert_keys_to_str(question_bank), ensure_ascii=False)
        
        headers = {
            "apikey": config["key"],
            "Authorization": f"Bearer {config['key']}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        
        payload = {
            "id": 1,
            "data": data_str
        }
        
        url = f"{config['url']}/rest/v1/question_bank"
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201, 204]:
            return True
        else:
            st.error(f"Lỗi Supabase: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        st.error(f"Lỗi lưu Supabase: {e}")
        return False


def _load_from_supabase(config) -> dict:
    """Tải dữ liệu từ Supabase qua REST API"""
    try:
        headers = {
            "apikey": config["key"],
            "Authorization": f"Bearer {config['key']}"
        }
        
        url = f"{config['url']}/rest/v1/question_bank?id=eq.1&select=data"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0:
                data_str = result[0]["data"]
                data = json.loads(data_str)
                return _convert_keys_to_int(data)
                
    except Exception as e:
        st.warning(f"Không thể tải từ Supabase: {e}")
    
    return DEFAULT_BANK.copy()


# ========== LOCAL FUNCTIONS ==========

def _save_to_local(question_bank: dict) -> bool:
    """Lưu dữ liệu ra file JSON local"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_convert_keys_to_str(question_bank), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Lỗi khi lưu local: {e}")
        return False


def _load_from_local() -> dict:
    """Tải dữ liệu từ file JSON local"""
    if not os.path.exists(DATA_FILE):
        return DEFAULT_BANK.copy()
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _convert_keys_to_int(data)
    except Exception as e:
        print(f"Lỗi khi tải local: {e}")
        return DEFAULT_BANK.copy()


# ========== PUBLIC API ==========

def save_question_bank(question_bank: dict) -> bool:
    """Lưu question_bank (tự động chọn Supabase hoặc local)"""
    config = _get_supabase_config()
    
    if config:
        return _save_to_supabase(config, question_bank)
    else:
        return _save_to_local(question_bank)


def load_question_bank() -> dict:
    """Tải question_bank (tự động chọn Supabase hoặc local)"""
    config = _get_supabase_config()
    
    if config:
        return _load_from_supabase(config)
    else:
        return _load_from_local()
