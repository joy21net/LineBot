import json
import urllib.request
import urllib.parse
import urllib.error

from flask import request, abort, render_template, jsonify
from linebot.v3.exceptions import InvalidSignatureError

# 악성 요청을 보낸 IP들을 저장하는 차단 목록 (서버가 재시작되면 초기화됨)
blocked_ips = set()

# 차단할 악성 경로 패턴들
MALICIOUS_PATTERNS = ["../", "..\\", "/cgi-bin/", "/bin/sh", "/etc/passwd", "php", ".env"]

def init_routes(app, handler):
    @app.before_request
    def filter_malicious_requests():
        # 1. 이미 차단된 IP인지 확인
        client_ip = request.remote_addr
        if client_ip in blocked_ips:
            return abort(403, description="Blocked IP")

        # 2. 경로 우회 및 쉘 실행 공격 패턴 검사
        path = request.path
        full_path = request.full_path if request.full_path else ""
        
        # 소문자로 변환하여 검사
        check_target = urllib.parse.unquote(full_path).lower()
        
        for pattern in MALICIOUS_PATTERNS:
            if pattern in check_target:
                # 악성 패턴 감지 시 IP 차단
                app.logger.warning(f"[SECURITY ALERT] Malicious request detected from IP: {client_ip}. Pattern: {pattern}. Blocking IP.")
                blocked_ips.add(client_ip)
                return abort(403, description="Forbidden")

    @app.route("/")
    def index():
        return render_template("linbot_v5.html")

    @app.route("/edu")
    def edu_page():
        return render_template("edu.html")

    @app.route("/liff")
    def liff_reserve():
        return render_template("liff/reserve.html")

    @app.route("/api/reservation", methods=["POST"])
    def api_reservation():
        data = request.get_json()
        if not data:
            return jsonify({"message": "잘못된 요청입니다."}), 400

        id_token = data.get("idToken")
        plan = data.get("plan")

        if not id_token:
            return jsonify({"message": "유효하지 않은 사용자입니다."}), 401

        verify_url = "https://api.line.me/oauth2/v2.1/verify"
        payload = {
            "id_token": id_token,
            "client_id": "2009473953"  # LINE Login 채널 ID
        }
        data_encoded = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(
            verify_url, 
            data=data_encoded, 
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        try:
            with urllib.request.urlopen(req) as response:
                verified = json.loads(response.read().decode('utf-8'))
                name = verified.get("name", "고객")
                
                # 여기서 DB 저장 처리 등을 할 수 있습니다.

                return jsonify({
                    "message": f"{name}님의 {plan} 예약이 저장되었습니다."
                })
        except urllib.error.HTTPError as e:
            app.logger.error(f"LINE verify error: {e.read().decode('utf-8')}")
            return jsonify({"message": "유효하지 않은 사용자입니다."}), 401
        except Exception as e:
            app.logger.error(f"Error during reservation: {e}")
            return jsonify({"message": "서버 오류가 발생했습니다."}), 500

    @app.route("/callback", methods=['POST'])
    def callback():
        # 라인 웹훅
        signature = request.headers.get('X-Line-Signature')
        body = request.get_data(as_text=True)
        app.logger.info(f"Request body: {body}")

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            app.logger.error("Invalid signature. Please check your LINE_CHANNEL_SECRET.")
            abort(400)

        return 'OK'
