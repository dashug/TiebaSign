# -*- coding:utf-8 -*-
import os
import requests
import hashlib
import time
import copy
import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API_URL
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"

ENV = os.environ

HEADERS = {
    'Host': 'tieba.baidu.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
}
SIGN_DATA = {
    '_client_type': '2',
    '_client_version': '9.7.8.0',
    '_phone_imei': '000000000000000',
    'model': 'MI+5',
    "net_type": "1",
}

# VARIABLE NAME
COOKIE = "Cookie"
BDUSS = "BDUSS"
EQUAL = r'='
EMPTY_STR = r''
TBS = 'tbs'
PAGE_NO = 'page_no'
ONE = '1'
TIMESTAMP = "timestamp"
DATA = 'data'
FID = 'fid'
SIGN_KEY = 'tiebaclient!!!'
UTF8 = "utf-8"
SIGN = "sign"
KW = "kw"

s = requests.Session()

def get_tbs(bduss):
    logger.info("获取tbs开始")
    headers = copy.copy(HEADERS)
    headers.update({COOKIE: EMPTY_STR.join([BDUSS, EQUAL, bduss])})
    response = None
    last_error = None
    for attempt in range(2):
        try:
            response = s.get(url=TBS_URL, headers=headers, timeout=5).json()
            break
        except Exception as e:
            last_error = e
            if attempt == 0:
                logger.warning("获取tbs失败，正在重试")
    if response is None:
        raise RuntimeError("获取tbs失败") from last_error
    if str(response.get('is_login')) != '1':
        raise RuntimeError("BDUSS无效或已过期，请更新GitHub Actions Secret")
    if TBS not in response:
        raise RuntimeError("tbs接口响应缺少tbs字段")
    tbs = response[TBS]
    logger.info("获取tbs结束")
    return tbs

def get_favorite(bduss):
    logger.info("获取关注的贴吧开始")
    returnData = {}
    i = 1
    data = {
        'BDUSS': bduss,
        '_client_type': '2',
        '_client_id': 'wappc_1534235498291_488',
        '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000',
        'from': '1008621y',
        'page_no': '1',
        'page_size': '200',
        'model': 'MI+5',
        'net_type': '1',
        'timestamp': str(int(time.time())),
        'vcode_tag': '11',
    }
    data = encodeData(data)
    try:
        res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
    except Exception as e:
        raise RuntimeError("获取关注的贴吧请求失败") from e
    error_code = str(res.get('error_code', '0'))
    if error_code != '0':
        error_msg = res.get('error_msg', '未知错误')
        raise RuntimeError("获取关注的贴吧失败：error_code=" + error_code + "，error_msg=" + str(error_msg))
    if 'forum_list' not in res:
        raise RuntimeError("关注贴吧接口响应缺少forum_list字段")
    returnData = res
    if res['forum_list'] == []:
        logger.info("未获取到关注的贴吧")
        return []
    if not isinstance(returnData['forum_list'], dict):
        raise RuntimeError("关注贴吧接口返回了无法识别的forum_list结构")
    if 'non-gconforum' not in returnData['forum_list']:
        returnData['forum_list']['non-gconforum'] = []
    if 'gconforum' not in returnData['forum_list']:
        returnData['forum_list']['gconforum'] = []
    while 'has_more' in res and res['has_more'] == '1':
        i = i + 1
        data = {
            'BDUSS': bduss,
            '_client_type': '2',
            '_client_id': 'wappc_1534235498291_488',
            '_client_version': '9.7.8.0',
            '_phone_imei': '000000000000000',
            'from': '1008621y',
            'page_no': str(i),
            'page_size': '200',
            'model': 'MI+5',
            'net_type': '1',
            'timestamp': str(int(time.time())),
            'vcode_tag': '11',
        }
        data = encodeData(data)
        try:
            res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
        except Exception as e:
            raise RuntimeError("获取关注的贴吧分页请求失败") from e
        error_code = str(res.get('error_code', '0'))
        if error_code != '0':
            error_msg = res.get('error_msg', '未知错误')
            raise RuntimeError("获取关注的贴吧分页失败：error_code=" + error_code + "，error_msg=" + str(error_msg))
        if 'forum_list' not in res:
            raise RuntimeError("关注贴吧分页响应缺少forum_list字段")
        if 'non-gconforum' in res['forum_list']:
            returnData['forum_list']['non-gconforum'].append(res['forum_list']['non-gconforum'])
        if 'gconforum' in res['forum_list']:
            returnData['forum_list']['gconforum'].append(res['forum_list']['gconforum'])

    t = []
    for i in returnData['forum_list']['non-gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    for i in returnData['forum_list']['gconforum']:
        if isinstance(i, list):
            for j in i:
                if isinstance(j, list):
                    for k in j:
                        t.append(k)
                else:
                    t.append(j)
        else:
            t.append(i)
    logger.info("获取关注的贴吧结束")
    return t

def encodeData(data):
    s = EMPTY_STR
    keys = data.keys()
    for i in sorted(keys):
        s += i + EQUAL + str(data[i])
    sign = hashlib.md5((s + SIGN_KEY).encode(UTF8)).hexdigest().upper()
    data.update({SIGN: str(sign)})
    return data

def client_sign(bduss, tbs, fid, kw):
    logger.info("开始签到贴吧：" + kw)
    data = copy.copy(SIGN_DATA)
    data.update({BDUSS: bduss, FID: fid, KW: kw, TBS: tbs, TIMESTAMP: str(int(time.time()))})
    data = encodeData(data)
    res = s.post(url=SIGN_URL, data=data, timeout=5).json()
    error_code = str(res.get('error_code', ''))
    if error_code == '0':
        logger.info("签到成功：" + kw)
    elif error_code == '160002':
        logger.info("今日已签到：" + kw)
    else:
        error_msg = res.get('error_msg', '未知错误')
        raise RuntimeError("签到失败：" + kw + "，error_code=" + error_code + "，error_msg=" + str(error_msg))
    return res

def main():
    if ('BDUSS' not in ENV):
        raise RuntimeError("未配置BDUSS")
    b = ENV['BDUSS'].split('#')
    for n, i in enumerate(b):
        logger.info("开始签到第" + str(n) + "个用户")
        tbs = get_tbs(i)
        favorites = get_favorite(i)
        for j in favorites:
            time.sleep(random.randint(1,5))
            client_sign(i, tbs, j["id"], j["name"])
        logger.info("完成第" + str(n) + "个用户签到")
    logger.info("所有用户签到结束")

if __name__ == '__main__':
    main()
