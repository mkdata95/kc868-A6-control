from flask import Flask, render_template, request, jsonify
import aiohttp
import asyncio
import sqlite3
import json
import threading
import time
from datetime import datetime, timedelta
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
        # 스케줄 데이터 초기화
        self.init_schedule_db()
        # 스위치 이름 데이터 초기화
        self.init_switch_names_db()
        # 스케줄러 시작
        self.start_scheduler()
        
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
                        
                        # 빠른 응답을 위한 짧은 타임아웃
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=1)) as response:
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
            
    def init_schedule_db(self):
        """스케줄 데이터베이스 초기화"""
        try:
            conn = sqlite3.connect('kc868_schedule.db')
            c = conn.cursor()
            
            # 스케줄 테이블 생성
            c.execute('''CREATE TABLE IF NOT EXISTS schedules
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         switch_num INTEGER,
                         day_of_week INTEGER,
                         time_on TEXT,
                         time_off TEXT,
                         enabled BOOLEAN,
                         name TEXT,
                         created_at TEXT)''')
            
            conn.commit()
            conn.close()
            logger.info("📅 스케줄 데이터베이스 초기화 완료")
            
        except Exception as e:
            logger.error(f"💥 스케줄 DB 초기화 오류: {e}")
            
    def start_scheduler(self):
        """백그라운드 스케줄러 시작"""
        def scheduler_worker():
            while True:
                try:
                    self.check_schedules()
                    time.sleep(30)  # 30초마다 체크
                except Exception as e:
                    logger.error(f"💥 스케줄러 오류: {e}")
                    time.sleep(60)  # 오류 시 1분 대기
                    
        thread = threading.Thread(target=scheduler_worker, daemon=True)
        thread.start()
        logger.info("⏰ 스케줄러 시작됨")
        
    def check_schedules(self):
        """스케줄 체크 및 실행"""
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_day = now.weekday()  # 0=월요일, 6=일요일
            
            conn = sqlite3.connect('kc868_schedule.db')
            c = conn.cursor()
            
            # 현재 시간과 요일에 맞는 스케줄 조회
            c.execute("""
                SELECT switch_num, time_on, time_off, name 
                FROM schedules 
                WHERE enabled = 1 AND day_of_week = ?
            """, (current_day,))
            
            schedules = c.fetchall()
            conn.close()
            
            for schedule in schedules:
                switch_num, time_on, time_off, name = schedule
                
                # ON 시간 체크
                if time_on and current_time == time_on:
                    logger.info(f"⏰ 스케줄 실행: 스위치{switch_num} ON ({name})")
                    asyncio.run(self.control_switch(switch_num, "ON"))
                
                # OFF 시간 체크
                if time_off and current_time == time_off:
                    logger.info(f"⏰ 스케줄 실행: 스위치{switch_num} OFF ({name})")
                    asyncio.run(self.control_switch(switch_num, "OFF"))
                    
        except Exception as e:
            logger.error(f"💥 스케줄 체크 오류: {e}")
            
    def get_schedules(self, switch_num=None):
        """스케줄 조회"""
        try:
            conn = sqlite3.connect('kc868_schedule.db')
            c = conn.cursor()
            
            if switch_num:
                c.execute("SELECT * FROM schedules WHERE switch_num = ? ORDER BY day_of_week, time_on", (switch_num,))
            else:
                c.execute("SELECT * FROM schedules ORDER BY switch_num, day_of_week, time_on")
                
            schedules = c.fetchall()
            conn.close()
            
            return [{
                'id': s[0], 'switch_num': s[1], 'day_of_week': s[2],
                'time_on': s[3], 'time_off': s[4], 'enabled': s[5],
                'name': s[6], 'created_at': s[7]
            } for s in schedules]
            
        except Exception as e:
            logger.error(f"💥 스케줄 조회 오류: {e}")
            return []
            
    def save_schedule(self, switch_num, day_of_week, time_on, time_off, name, enabled=True):
        """스케줄 저장"""
        try:
            conn = sqlite3.connect('kc868_schedule.db')
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO schedules (switch_num, day_of_week, time_on, time_off, enabled, name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (switch_num, day_of_week, time_on, time_off, enabled, name, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📅 스케줄 저장: 스위치{switch_num} {name}")
            return True
            
        except Exception as e:
            logger.error(f"💥 스케줄 저장 오류: {e}")
            return False
            
    def delete_schedule(self, schedule_id):
        """스케줄 삭제"""
        try:
            conn = sqlite3.connect('kc868_schedule.db')
            c = conn.cursor()
            
            c.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"🗑️ 스케줄 삭제: ID {schedule_id}")
            return True
            
        except Exception as e:
            logger.error(f"💥 스케줄 삭제 오류: {e}")
            return False
            
    def init_switch_names_db(self):
        """스위치 이름 데이터베이스 초기화"""
        try:
            conn = sqlite3.connect('kc868_switch_names.db')
            c = conn.cursor()
            
            # 스위치 이름 테이블 생성
            c.execute('''CREATE TABLE IF NOT EXISTS switch_names
                        (switch_num INTEGER PRIMARY KEY,
                         name TEXT NOT NULL,
                         icon TEXT DEFAULT 'fa-power-off',
                         updated_at TEXT)''')
            
            # 기본 설정 (없는 경우에만)
            default_settings = [
                ('메인 조명', 'fa-lightbulb'), ('복도 조명', 'fa-lightbulb'), ('에어컨', 'fa-snowflake'),
                ('작업 장비', 'fa-cogs'), ('보안등', 'fa-shield-alt'), ('비상 전원', 'fa-battery-full')
            ]
            
            for i, (name, icon) in enumerate(default_settings, 1):
                c.execute("SELECT name FROM switch_names WHERE switch_num = ?", (i,))
                if not c.fetchone():
                    c.execute("""
                        INSERT INTO switch_names (switch_num, name, icon, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (i, name, icon, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            logger.info("🏷️ 스위치 이름 데이터베이스 초기화 완료")
            
        except Exception as e:
            logger.error(f"💥 스위치 이름 DB 초기화 오류: {e}")
            
    def get_switch_names(self):
        """모든 스위치 이름 조회"""
        try:
            conn = sqlite3.connect('kc868_switch_names.db')
            c = conn.cursor()
            
            c.execute("SELECT switch_num, name, icon FROM switch_names ORDER BY switch_num")
            switches = c.fetchall()
            conn.close()
            
            return {
                str(switch_num): {
                    'name': name, 
                    'icon': icon or 'fa-power-off'
                } for switch_num, name, icon in switches
            }
            
        except Exception as e:
            logger.error(f"💥 스위치 이름 조회 오류: {e}")
            # 기본값 반환
            return {
                "1": {"name": "메인 조명", "icon": "fa-lightbulb"}, 
                "2": {"name": "복도 조명", "icon": "fa-lightbulb"}, 
                "3": {"name": "에어컨", "icon": "fa-snowflake"},
                "4": {"name": "작업 장비", "icon": "fa-cogs"}, 
                "5": {"name": "보안등", "icon": "fa-shield-alt"}, 
                "6": {"name": "비상 전원", "icon": "fa-battery-full"}
            }
            
    def update_switch_name(self, switch_num, name):
        """스위치 이름 업데이트"""
        try:
            conn = sqlite3.connect('kc868_switch_names.db')
            c = conn.cursor()
            
            c.execute("""
                UPDATE switch_names 
                SET name = ?, updated_at = ?
                WHERE switch_num = ?
            """, (name, datetime.now().isoformat(), switch_num))
            
            # 해당 스위치가 없으면 새로 생성
            if c.rowcount == 0:
                c.execute("""
                    INSERT INTO switch_names (switch_num, name, icon, updated_at)
                    VALUES (?, ?, 'fa-power-off', ?)
                """, (switch_num, name, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"🏷️ 스위치{switch_num} 이름 변경: '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"💥 스위치 이름 업데이트 오류: {e}")
            return False
            
    def update_switch_icon(self, switch_num, icon):
        """스위치 아이콘 업데이트"""
        try:
            conn = sqlite3.connect('kc868_switch_names.db')
            c = conn.cursor()
            
            c.execute("""
                UPDATE switch_names 
                SET icon = ?, updated_at = ?
                WHERE switch_num = ?
            """, (icon, datetime.now().isoformat(), switch_num))
            
            # 해당 스위치가 없으면 새로 생성
            if c.rowcount == 0:
                c.execute("""
                    INSERT INTO switch_names (switch_num, name, icon, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (switch_num, f'스위치 {switch_num}', icon, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"🎨 스위치{switch_num} 아이콘 변경: '{icon}'")
            return True
            
        except Exception as e:
            logger.error(f"💥 스위치 아이콘 업데이트 오류: {e}")
            return False

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

@app.route('/api/schedules')
def get_schedules():
    """스케줄 조회 API"""
    try:
        switch_num = request.args.get('switch_num', type=int)
        schedules = controller.get_schedules(switch_num)
        return jsonify(schedules)
    except Exception as e:
        logger.error(f"💥 스케줄 조회 오류: {e}")
        return jsonify([]), 500

@app.route('/api/schedules', methods=['POST'])
def save_schedule():
    """스케줄 저장 API"""
    try:
        data = request.get_json()
        
        success = controller.save_schedule(
            switch_num=data['switch_num'],
            day_of_week=data['day_of_week'],
            time_on=data.get('time_on'),
            time_off=data.get('time_off'),
            name=data['name'],
            enabled=data.get('enabled', True)
        )
        
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"💥 스케줄 저장 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """스케줄 삭제 API"""
    try:
        success = controller.delete_schedule(schedule_id)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"💥 스케줄 삭제 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/switch-names')
def get_switch_names():
    """스위치 이름 조회 API"""
    try:
        names = controller.get_switch_names()
        return jsonify(names)
    except Exception as e:
        logger.error(f"💥 스위치 이름 조회 오류: {e}")
        return jsonify({}), 500

@app.route('/api/switch-names/<int:switch_num>', methods=['PUT'])
def update_switch_name(switch_num):
    """스위치 이름 업데이트 API"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'message': '이름이 비어있습니다'}), 400
            
        if len(name) > 20:
            return jsonify({'success': False, 'message': '이름이 너무 깁니다 (최대 20자)'}), 400
        
        success = controller.update_switch_name(switch_num, name)
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"💥 스위치 이름 업데이트 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/switch-icons/<int:switch_num>', methods=['PUT'])
def update_switch_icon(switch_num):
    """스위치 아이콘 업데이트 API"""
    try:
        data = request.get_json()
        icon = data.get('icon', '').strip()
        
        if not icon:
            return jsonify({'success': False, 'message': '아이콘이 선택되지 않았습니다'}), 400
            
        # 기본적인 보안 검사 (fa- 접두사 확인)
        if not icon.startswith('fa-'):
            return jsonify({'success': False, 'message': '올바르지 않은 아이콘 형식입니다'}), 400
        
        success = controller.update_switch_icon(switch_num, icon)
        return jsonify({'success': success})
        
    except Exception as e:
        logger.error(f"💥 스위치 아이콘 업데이트 오류: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/reset-icons', methods=['POST'])
def reset_icons():
    """모든 아이콘을 기본값으로 리셋"""
    try:
        safe_icons = {
            1: {"icon": "fa-lightbulb", "name": "메인 조명"},
            2: {"icon": "fa-tv", "name": "TV"},
            3: {"icon": "fa-snowflake", "name": "에어컨"},
            4: {"icon": "fa-fan", "name": "선풍기"},
            5: {"icon": "fa-music", "name": "오디오"},
            6: {"icon": "fa-home", "name": "기타"}
        }
        
        conn = sqlite3.connect('kc868_switch_names.db')
        cursor = conn.cursor()
        
        for switch_num, settings in safe_icons.items():
            # 아이콘과 이름 모두 리셋
            cursor.execute("""
                UPDATE switch_names 
                SET icon = ?, name = ?, updated_at = ?
                WHERE switch_num = ?
            """, (settings["icon"], settings["name"], datetime.now().isoformat(), switch_num))
            
            # 해당 스위치가 없으면 새로 생성
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO switch_names (switch_num, name, icon, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (switch_num, settings["name"], settings["icon"], datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info("🔄 모든 아이콘과 이름이 기본값으로 리셋되었습니다")
        return jsonify({"success": True, "message": "모든 아이콘과 이름이 리셋되었습니다. 페이지를 새로고침하세요."})
        
    except Exception as e:
        logger.error(f"💥 아이콘 리셋 오류: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    print("🚀 KC868-A6 웹 서버 시작")
    print(f"📡 KC868-A6 IP: {controller.ip_address}")
    print("🌐 웹 인터페이스: http://localhost:5000")
    print("⚠️  먼저 WiFi 설정을 확인하고 ESPHome 펌웨어를 업로드하세요!")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 