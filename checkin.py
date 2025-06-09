import requests
import json
import os
from typing import Optional
from pypushdeer import PushDeer

def send_pushdeer_notification(sckey: str, title: str, content: str) -> None:
    """发送 PushDeer 通知"""
    if not sckey:
        print("未提供 PushDeer SENDKEY，跳过通知")
        return
    try:
        pushdeer = PushDeer(pushkey=sckey)
        pushdeer.send_text(title, desp=content)
        print("PushDeer 通知发送成功")
    except Exception as e:
        print(f"PushDeer 通知发送失败: {e}")

def checkin_glados(cookie: str) -> Optional[dict]:
    """执行 Glados 签到并获取状态"""
    check_in_url = "https://glados.space/api/user/checkin"
    status_url = "https://glados.space/api/user/status"
    headers = {
        'cookie': cookie,
        'referer': 'https://glados.space/console/checkin',
        'origin': 'https://glados.space',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
        'content-type': 'application/json;charset=UTF-8'
    }
    payload = {'token': 'glados.one'}

    try:
        # 签到请求
        checkin = requests.post(check_in_url, headers=headers, data=json.dumps(payload), timeout=10)
        print(f"签到请求状态码: {checkin.status_code}")
        print(f"签到请求响应: {checkin.text}")

        # 状态请求
        state = requests.get(status_url, headers=headers, timeout=10)
        print(f"状态请求状态码: {state.status_code}")
        print(f"状态请求响应: {state.text}")

        # 检查签到响应
        try:
            checkin_data = checkin.json()
        except json.JSONDecodeError:
            print("签到API返回非JSON格式")
            return {'email': 'Unknown', 'message': '签到API返回非JSON格式', 'points': 0, 'left_days': 'error'}

        # 检查状态响应
        try:
            state_data = state.json()
        except json.JSONDecodeError:
            print("状态API返回非JSON格式")
            return {'email': 'Unknown', 'message': '状态API返回非JSON格式', 'points': 0, 'left_days': 'error'}

        # 验证响应结构
        if 'data' not in state_data:
            print(f"状态API未返回'data'键，完整响应: {state_data}")
            return {'email': 'Unknown', 'message': f"状态API未返回'data'键: {state_data}", 'points': 0, 'left_days': 'error'}

        # 提取数据
        email = state_data['data'].get('email', 'Unknown')
        left_days = state_data['data'].get('leftDays', '0')
        try:
            left_days = int(float(left_days)) if left_days else 0
        except (ValueError, TypeError):
            left_days = 'error'

        message = checkin_data.get('message', '未知签到结果')
        points = checkin_data.get('points', 0)

        return {
            'email': email,
            'message': message,
            'points': points,
            'left_days': str(left_days)
        }

    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return {'email': 'Unknown', 'message': f'请求失败: {e}', 'points': 0, 'left_days': 'error'}

def main():
    # 获取环境变量
    sckey = os.environ.get("SENDKEY", "")
    cookies = os.environ.get("COOKIES", "").split("&") if os.environ.get("COOKIES") else []

    if not cookies or cookies == [""]:
        print("未获取到COOKIES变量")
        send_pushdeer_notification(sckey, "Glados 签到失败", "未找到 COOKIES!")
        exit(1)

    success, fail, repeats = 0, 0, 0
    context = ""

    for cookie in cookies:
        if not cookie.strip():
            print("跳过空cookie")
            continue

        result = checkin_glados(cookie)
        email = result['email']
        message = result['message']
        points = result['points']
        left_days = result['left_days']

        # 判断签到结果
        if "Checkin! Got" in message:
            success += 1
            message_status = f"签到成功，会员点数 + {points}"
        elif "Checkin Repeats!" in message:
            repeats += 1
            message_status = "重复签到，明天再来"
        else:
            fail += 1
            message_status = f"签到失败: {message}"

        log = f"账号: {email}, P: {points}, 剩余: {left_days} 天 | {message_status}"
        print(log)
        context += log + "\n"

    # 发送通知
    title = f"Glados, 成功{success}, 失败{fail}, 重复{repeats}"
    print("推送内容:\n", context)
    send_pushdeer_notification(sckey, title, context)

if __name__ == "__main__":
    main()
