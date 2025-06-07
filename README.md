# 🏠 KC868-A6 완전한 스마트홈 제어 시스템

> **ESPHome + Flask 기반의 완벽한 릴레이 제어 시스템**  
> 실제 하드웨어 제어 + 웹 인터페이스 + 안정적인 상태 관리

## 🎯 프로젝트 개요

KC868-A6 ESP32 기반 릴레이 보드를 사용한 완전한 스마트홈 제어 시스템입니다.  
**실제 릴레이 제어**가 가능하며, **안정적인 웹 인터페이스**를 제공합니다.

## ✨ 주요 기능

### 🔧 하드웨어 제어
- ✅ **6개 릴레이 완벽 제어** (실제 하드웨어 ON/OFF)
- ✅ **PCF8574 I2C 확장칩** 활용
- ✅ **올바른 핀 매핑** (SCL=GPIO15, SDA=GPIO4)

### 🌐 웹 인터페이스  
- ✅ **Flask 웹서버** (localhost:5000)
- ✅ **실시간 상태 표시** (초록/회색 토글)
- ✅ **안정적인 상태 캐시** 시스템
- ✅ **반응형 UI** (모던한 디자인)

### 📡 API 통합
- ✅ **ESPHome REST API** 활용
- ✅ **한글 스위치명 지원** (스위치1 → ___1)
- ✅ **POST 방식 제어** + **GET 방식 상태조회**

## 🚀 빠른 시작

### 1. 하드웨어 연결
```
KC868-A6 → USB-C 케이블 → PC
KC868-A6 → 12V 외부전원 (릴레이 작동용)
```

### 2. ESPHome 펌웨어 업로드
```bash
esphome run kc868-a6-basic.yaml --device COM4
```

### 3. Flask 웹서버 실행
```bash
pip install -r requirements.txt
python app.py
```

### 4. 웹 인터페이스 접속
```
http://localhost:5000  # Flask 웹서버
http://192.168.0.100   # ESPHome 직접 접속
```

## 📁 프로젝트 구조

```
KC8668-A6/
├── 🔧 하드웨어 설정
│   └── kc868-a6-basic.yaml        # ESPHome 설정
├── 🌐 웹서버
│   ├── app.py                     # Flask 메인 서버
│   ├── templates/dashboard.html   # 웹 인터페이스
│   └── requirements.txt           # Python 의존성
├── 📚 문서
│   ├── 개발주의사항.md              # 🌟 핵심 개발 가이드
│   ├── KC868-A6-프로젝트-아이디어.md
│   └── 안드로이드-RS485-제어-가이드.md
└── 🗃️ 기타
    ├── .gitignore
    └── kc868_logs.db              # 제어 로그
```

## 🔑 핵심 기술 정보

### ESPHome API 엔드포인트
```python
# 제어 (POST)
POST http://192.168.0.100/switch/___1/turn_on
POST http://192.168.0.100/switch/___1/turn_off

# 상태 조회 (GET)
GET http://192.168.0.100/switch/___1
# 응답: {"id": "switch-___1", "state": "ON", "value": true}
```

### I2C 설정 (중요!)
```yaml
i2c:
  sda: GPIO4
  scl: GPIO15  # ⚠️ GPIO15 (많은 예제가 GPIO5로 잘못 표기!)
```

### PCF8574 주소
```yaml
pcf8574:
  - id: relay_outputs
    address: 0x24      # 릴레이 출력
  - id: digital_inputs  
    address: 0x22      # 디지털 입력
```

## 🐛 문제 해결

### 자주 발생하는 문제
1. **릴레이가 안 켜짐** → I2C 핀 확인 (SCL=GPIO15)
2. **상태가 불안정** → 캐시 시스템으로 해결됨
3. **API 404 오류** → `___숫자` 엔드포인트 패턴 확인

### 디버깅
```bash
# ESPHome 로그 확인
esphome logs kc868-a6-basic.yaml --device COM4

# Flask 로그 확인  
python app.py  # 콘솔에서 로그 확인
```

## 📊 성과 및 해결된 문제

### ✅ 성공적으로 해결한 문제들
- 🔧 **I2C 핀 매핑 오류** → GPIO15 사용으로 해결
- 🌐 **API 엔드포인트 발견** → `___숫자` 패턴 규명  
- 🎯 **상태 표시 불안정** → 캐시 시스템으로 안정화
- 📱 **웹 인터페이스 구현** → 반응형 UI 완성
- 📝 **완벽한 문서화** → 개발주의사항.md 작성

### 🎉 최종 결과
- **실제 릴레이 제어** 100% 작동
- **웹 인터페이스** 완벽 구현
- **안정적인 상태 표시** 문제 해결
- **완전한 개발 가이드** 문서화

## 🛠️ 기술 스택

- **하드웨어**: KC868-A6 (ESP32 + PCF8574)
- **펌웨어**: ESPHome 2025.5.2
- **백엔드**: Python Flask
- **프론트엔드**: HTML5 + CSS3 + JavaScript
- **통신**: REST API (HTTP)
- **데이터베이스**: SQLite (로그)

## 📞 지원 및 문의

- **문서**: [`개발주의사항.md`](./개발주의사항.md) ← 🌟 **핵심 가이드**
- **GitHub Issues**: [이슈 등록](https://github.com/mkdata95/kc868-A6-control/issues)
- **KC868-A6 공식**: [KinCony 포럼](https://www.kincony.com/forum/)

## 📜 라이선스

MIT License - 자유롭게 사용하세요!

---

**⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!**

> 💡 **완전한 개발 과정과 모든 해결 방법은 [`개발주의사항.md`](./개발주의사항.md)에 상세히 기록되어 있습니다.** 