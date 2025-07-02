import hashlib
import os
from pathlib import Path
import threading
import time
import traceback
import shutil

from filelock import FileLock

from configs import *
import configs
from utils import log
from enum import Enum

# cache structure:
#
# .cache/{cache_key}/.meta
# {id in hex} {file type id} {file name} {last hit timestamp} {size in bytes}
#
# .cache/{cache_key}/{file id in hex}

# cache init
Path(CACHE_DIR).mkdir(exist_ok=True)

class CacheType(Enum):
    WEB_FILE = 1
    CERT = 2

def _parse_cache_meta_line(line: str):
    """解析元数据行"""
    line_parts = line.strip().split('\t')
    if len(line_parts) != 5:
        raise ValueError("Invalid meta data line")
    return {
        'id': line_parts[0],
        'type': CacheType(int(line_parts[1])),
        'name': line_parts[2],
        'last_hit': float(line_parts[3]),
        'size': int(line_parts[4])
    }

def _parse_cache_meta(meta_str: str):
    """解析元数据"""
    l = []
    for line in meta_str.split('\n'):
        if line.strip() == "":
            continue
        l.append(_parse_cache_meta_line(line))
    return l

def _save_cache_meta(meta: list):
    """保存元数据"""
    return '\n'.join(f"{m['id']}\t{m['type'].value}\t{m['name']}\t{m['last_hit']}\t{m['size']}" for m in meta)

def _get_available_cache_id(meta: list):
    """获取可用缓存ID"""
    used_ids = set(m['id'] for m in meta)
    for i in range(16**16):
        if str(i.to_bytes(2, 'big').hex()) not in used_ids:
            return str(i.to_bytes(2, 'big').hex())
    raise ValueError("No available cache id")

def _get_cache_key(type: CacheType, name: str):
    """生成缓存键"""
    return hashlib.sha256((type.name + "#" + name).encode('utf-8')).hexdigest()

def _check_disk_space():
    """检查磁盘空间是否充足"""
    if not Path(CACHE_DIR).exists():
        return True
    used = sum(f.stat().st_size for f in Path(CACHE_DIR).glob('*') if f.is_file())
    return used < DISK_CACHE_MAX_SIZE
    

def save_to_cache(type: CacheType, name: str, data: bytes):
    """保存数据到缓存系统"""
    # log(f"Attempting to save cache: type={type}, name={name}, with_cache={configs.with_cache}")
    if (not configs.with_cache) and type == CacheType.WEB_FILE:
        return False

    data_size = len(data)
    if data_size > DISK_CACHE_MAX_FILE_SIZE:
        log(f"Jummping cache for file {name}: too large ({data_size / 1024 / 1024:.2f} MB)")
        return False
    
    if data_size < DISK_CACHE_MIN_FILE_SIZE and type == CacheType.WEB_FILE:
        log(f"Jummping cache for file {name}: too small ({data_size / 1024 / 1024:.2f} MB)")
        return False
    
    if not _check_disk_space():
        log(f"Jummping cache for file {name}: no space left")
        return False
    
    cache_key = _get_cache_key(type, name)
    cache_dir = CACHE_DIR + "/" + cache_key
    Path(cache_dir).mkdir(exist_ok=True)

    meta_file = CACHE_DIR + "/" + cache_key + "/.meta"
    if not Path(meta_file).exists():
        with open(meta_file, 'w') as f:
            f.write("")

    locker = FileLock(meta_file + ".lock")
    try:
        with locker.acquire(timeout=10):
            meta = None
            with open(meta_file) as f:
                meta = _parse_cache_meta(f.read())
            for m in meta:
                if m['name'] == name and m['type'] == type:
                    log(f"Jummping cache for file {type.name}#{name}: already exist")
                    return False
            
            cache_id = _get_available_cache_id(meta)
            meta.append({
                'id': cache_id,
                'type': type,
                'name': name,
                'last_hit': time.time(),
                'size': data_size
            })
            with open(meta_file, 'w') as f:
                f.write(_save_cache_meta(meta))
            
            cache_file = cache_dir + "/" + cache_id
            with open(cache_file, 'wb') as f:
                f.write(data)
            return True
    except Exception as e:
        log(f"Failed to check cache: {e}")
        traceback.print_exc()
        return False
    
def get_path_from_cache(type: CacheType, name: str):
    """从缓存中获取数据路径"""
    cache_key = _get_cache_key(type, name)
    cache_dir = CACHE_DIR + "/" + cache_key
    if not Path(cache_dir).exists():
        return None
    
    meta_file = CACHE_DIR + "/" + cache_key + "/.meta"
    if not Path(meta_file).exists():
        return None
    
    locker = FileLock(meta_file + ".lock")
    try:
        with locker.acquire(timeout=10):
            meta = None
            with open(meta_file) as f:
                meta = _parse_cache_meta(f.read())
            for m in meta:
                if m['name'] == name and m['type'] == type:
                    cache_file = cache_dir + "/" + m['id']
                    if not Path(cache_file).exists():
                        raise ValueError("Cache file not found, but meta data exists")
                    m['last_hit'] = time.time()
                    with open(meta_file, 'w') as f:
                        f.write(_save_cache_meta(meta))

                    log(f"Cache hit for file {type.name}#{name}: {m['size'] / 1024 / 1024:.2f} MB")
                    return cache_file
            return None
    except Exception as e:
        log(f"Failed to get cache path: {e}")
        traceback.print_exc()
        return None

def get_from_cache(type: CacheType, name: str):
    """从缓存中获取数据"""
    if not configs.with_cache:
        return None

    path = get_path_from_cache(type, name)
    if path is None:
        return None
    
    locker = FileLock(path + ".lock")
    try:
        with locker.acquire(timeout=10):
            with open(path, 'rb') as f:
                return f.read()
    except Exception as e:
        log(f"Failed to get cache: {e}")
        traceback.print_exc()
        return None

def _clean_cache():
    """定期清理过期缓存"""
    while True:
        now = time.time()
        log("Cleaning cache...")
        for cache_key in os.listdir(CACHE_DIR):
            meta_file = CACHE_DIR + "/" + cache_key + "/.meta"
            if not Path(meta_file).exists():
                shutil.rmtree(CACHE_DIR + "/" + cache_key, ignore_errors=True) # ignore errors
                continue

            locker = FileLock(meta_file + ".lock")
            try:
                with locker.acquire(timeout=10):
                    meta = None
                    with open(meta_file) as f:
                        meta = _parse_cache_meta(f.read())

                    expired_ids = [m['id'] for m in meta if m['last_hit'] + CACHE_EXPIRE_SECONDS < now]
                    for expired_id in expired_ids:
                        cache_file = CACHE_DIR + "/" + cache_key + "/" + expired_id
                        if Path(cache_file).exists():
                            os.remove(cache_file) # ignore errors
                            log(f"Cleaned cache file {cache_file}")
                        meta = [m for m in meta if m['id'] != expired_id]

                    if len(meta) == 0:
                        os.remove(meta_file) # ignore errors
                        shutil.rmtree(CACHE_DIR + "/" + cache_key, ignore_errors=True) # ignore errors
                        log(f"Cleaned cache directory {CACHE_DIR + '/' + cache_key}")
                    else:
                        with open(meta_file, 'w') as f:
                            f.write(_save_cache_meta(meta))
            except Exception as e:
                log(f"Failed to clean cache: {e}")
                traceback.print_exc()
        log("Cleaning cache done")
        time.sleep(CACHE_EXPIRE_SECONDS)  # 每24小时清理一次
        
def manual_clean_cache():
    """手动清理所有缓存，忽略有效期限制"""
    log("Cleaning all cache...")
    for cache_key in os.listdir(CACHE_DIR):
        cache_dir = CACHE_DIR + "/" + cache_key
        meta_file = CACHE_DIR + "/" + cache_key + "/.meta"
        if not Path(meta_file).exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
            continue

        locker = FileLock(meta_file + ".lock")
        try:
            with locker.acquire(timeout=10):
                with open(meta_file) as f:
                    meta = _parse_cache_meta(f.read())
                
                # 删除所有缓存项（忽略过期时间）
                for m in meta:
                    cache_file = CACHE_DIR + "/" + cache_key + "/" + m['id']
                    if Path(cache_file).exists():
                        os.remove(cache_file)
                        log(f"Cleaned cache file {cache_file}")
                
                # 删除元数据文件和目录
                os.remove(meta_file)
                shutil.rmtree(cache_dir, ignore_errors=True)
                log(f"Cleaned cache directory {cache_dir}")
                
        except Exception as e:
            log(f"Failed to clean cache: {e}")
            traceback.print_exc()
    
    log("Cleaning all cache done")

def chose_clean_ways(manual_clean=False):
    """
    Args:
        manual_clean (bool): 是否执行手动清理
    """
    # 始终启动定时清理线程
    threading.Thread(target=_clean_cache, daemon=True).start()
    
    # 根据参数决定是否执行手动清理
    if manual_clean:
        # manual_clean_cache()
        threading.Thread(target=manual_clean_cache, daemon=True).start()