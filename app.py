from flask import Flask, render_template, request, jsonify
import aiohttp
import asyncio
import sqlite3
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class KC868Controller:
        
    async def control_switch(self, switch_num, action):
        """스위치 제어 (ESPHome API 사용)"""
        try:
            # ESPHome 표준 엔드포인트 (개발주의사항.md 기반)
            entity_name = f"스위치{switch_num}"  # ESPHome에서 설정한 정확한 이름
            esphome_action = "turn_on" if action.upper() == "ON" else "turn_off"
            
            # ESPHome REST API 엔드포인트들 (실제 확인된 형식)
            possible_urls = [
                f"{self.base_url}/switch/___{switch_num}/{esphome_action}",      # /switch/___1/turn_on (실제 형식)
            ]
            
            async with aiohttp.ClientSession() as session:
                for url in possible_urls:
                    try:
                        logger.info(f"🔌 시도: {url}")
                        
                        # ESPHome은 POST 방식 사용 (공식 문서 확인)
                        async with session.post(
                            url,
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            
                            content = await response.text()
                            logger.info(f"📡 응답 {response.status}: {content[:100]}...")
                            
                            if response.status == 200:
                                logger.info(f"✅ 성공! 스위치{switch_num} {action}")
                                # 제어 성공 시 캐시 즉시 업데이트
                                self.last_known_status[f"스위치{switch_num}"] = action.upper()
                                self.log_action(switch_num, action)
                                return True
                                
                    except Exception as e:
                        logger.warning(f"❌ 실패 {url}: {e}")
                        continue
                
                # 모든 URL 실패시 데모 모드
                logger.warning(f"🔄 데모 모드: 스위치{switch_num} {action}")
                self.log_action(switch_num, action, demo=True)
                return False
                
        except Exception as e:
            logger.error(f"💥 컨트롤 오류: {e}")
            return False
    
    def __init__(self, ip_address="192.168.0.100"):
        self.ip_address = ip_address
        self.base_url = f"http://{ip_address}"
        # 상태 캐시 추가 (안정성을 위해)
        self.last_known_status = {f"스위치{i}": "OFF" for i in range(1, 7)}
        
    async def get_switch_status(self):
        """모든 스위치 상태 조회 (안정성 개선)"""
        try:
            status = {}
            async with aiohttp.ClientSession() as session:
                # 각 스위치별로 개별 상태 조회
                for switch_num in range(1, 7):  # 스위치 1~6
                    switch_key = f"스위치{switch_num}"
                    try:
                        # 실제 ESPHome API 엔드포인트 사용
                        url = f"{self.base_url}/switch/___{switch_num}"
                        
                        # 타임아웃을 좀 더 길게 설정
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                            if response.status == 200:
                                data = await response.json()
                                # ESPHome API 응답 형식: {"id": "switch-___1", "state": "ON", "value": true}
                                switch_state = data.get('state', self.last_known_status[switch_key])
                                status[switch_key] = switch_state
                                # 성공적으로 조회한 경우만 캐시 업데이트
                                self.last_known_status[switch_key] = switch_state
                                logger.debug(f"📊 스위치{switch_num} 상태: {switch_state}")
                            else:
                                # 실패 시 이전 상태 유지
                                status[switch_key] = self.last_known_status[switch_key]
                                logger.warning(f"⚠️ 스위치{switch_num} 상태 조회 실패 (HTTP {response.status}) - 이전 상태 유지")
                                
                    except Exception as e:
                        # 네트워크 오류 시 이전 상태 유지
                        status[switch_key] = self.last_known_status[switch_key]
                        logger.warning(f"⚠️ 스위치{switch_num} 상태 조회 오류: {e} - 이전 상태 유지")
                
                return status
                
        except Exception as e:
            logger.error(f"💥 상태 조회 전체 오류: {e} - 이전 상태 반환")
            # 전체 실패 시 이전 상태 반환
            return self.last_known_status.copy()
    
    def log_action(self, switch_num, action, demo=False):
        """동작 로그 기록"""
        try:
            conn = sqlite3.connect('kc868_logs.db')
            c = conn.cursor()
            
            # 테이블 생성
            c.execute('''CREATE TABLE IF NOT EXISTS logs
                        (timestamp TEXT, switch_num INTEGER, action TEXT, demo BOOLEAN)''')
            
            # 로그 삽입
            status = "데모" if demo else "실제"
            c.execute("INSERT INTO logs VALUES (?, ?, ?, ?)",
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), switch_num, action, demo))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📝 로그 기록: 스위치{switch_num} {action} ({status})")
            
        except Exception as e:
            logger.error(f"💥 로그 오류: {e}")

# KC868 컨트롤러 인스턴스
controller = KC868Controller()

@app.route('/')
def dashboard():
    """메인 대시보드"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """모든 스위치 상태 조회 API"""
    try:
        logger.debug("📊 상태 조회 요청")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        status = loop.run_until_complete(controller.get_switch_status())
        loop.close()
        logger.debug(f"📊 상태 결과: {status}")
        return jsonify(status)
    except Exception as e:
        logger.error(f"❌ 상태 조회 오류: {e}")
        # 데모 데이터 반환
        return jsonify({
            "스위치1": "OFF", "스위치2": "OFF", "스위치3": "OFF",
            "스위치4": "OFF", "스위치5": "OFF", "스위치6": "OFF"
        })

@app.route('/api/control', methods=['POST'])
def control():
    """스위치 제어 API"""
    try:
        data = request.get_json()
        switch_num = data.get('switch')
        action = data.get('action')
        
        logger.info(f"🎮 제어 요청: 스위치{switch_num} {action}")
        
        # 비동기 함수 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(controller.control_switch(switch_num, action))
        loop.close()
        
        return jsonify({
            'success': success,
            'message': f'스위치{switch_num} {action} {"성공" if success else "실패"}'
        })
        
    except Exception as e:
        logger.error(f"💥 제어 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """로그 조회 API"""
    try:
        conn = sqlite3.connect('kc868_logs.db')
        c = conn.cursor()
        c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100")
        logs = c.fetchall()
        conn.close()
        
        return jsonify([{
            'timestamp': log[0],
            'switch_num': log[1], 
            'action': log[2],
            'demo': log[3]
        } for log in logs])
        
    except Exception as e:
        logger.error(f"💥 로그 조회 오류: {e}")
        return jsonify([])

if __name__ == '__main__':
    print("🚀 KC868-A6 웹 서버 시작")
    print(f"📡 KC868-A6 IP: {controller.ip_address}")
    print("🌐 웹 인터페이스: http://localhost:5000")
    print("⚠️  먼저 WiFi 설정을 확인하고 ESPHome 펌웨어를 업로드하세요!")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 