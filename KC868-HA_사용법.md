# KC868-HA ESPHome 컴포넌트 사용법

## 개요
KC868-HA는 KinCony에서 제작한 Home Assistant 통합을 위한 릴레이 컨트롤러 보드입니다. 이 ESPHome 컴포넌트를 사용하면 ESP32와 KC868-HA 보드를 연결하여 Home Assistant에서 사용할 수 있습니다.

## 설치 완료 상태
✅ **ESPHome KC868-HA 컴포넌트 설치 완료!**

- GitHub 리포지토리: https://github.com/hzkincony/esphome-kc868-ha
- 버전: v3.0.1
- ESPHome 버전: 2025.5.2
- 컴파일 테스트: 성공

## 주요 기능

### 1. Binary Sensor (입력 감지)
- KC868-HA 보드의 K1~K6 입력 핀에서 신호 변화를 감지
- Home Assistant에서 각 입력의 상태를 확인 가능

### 2. Switch (출력 제어)
- KC868-HA 보드의 D1~D6 출력 핀을 제어
- Home Assistant에서 각 출력을 켜고 끌 수 있음

### 3. UART 통신
- ESP32와 KC868-HA 보드 간 RS485 통신
- TX: GPIO 1, RX: GPIO 3, 9600 baud rate

## 설정 파일 예제

```yaml
esphome:
  name: kc868-ha-test

esp32:
  board: esp32dev
  framework:
    type: arduino

wifi:
  ssid: "YOUR_WIFI_SSID"
  password: "YOUR_WIFI_PASSWORD"
  ap:
    ssid: "KC868-HA Fallback Hotspot"
    password: "12345678"

captive_portal:
logger:
  baud_rate: 0

api:

ota:
  - platform: esphome
    password: "YOUR_OTA_PASSWORD"

web_server:
  port: 80

# GitHub에서 외부 컴포넌트 가져오기
external_components:
  - source:
      type: git
      url: https://github.com/hzkincony/esphome-kc868-ha
      ref: v3.0.1

# UART 설정
uart:
  - id: myuart1
    tx_pin: 1
    rx_pin: 3
    baud_rate: 9600

# KC868-HA 컴포넌트
kc868_ha:

# 입력 센서 (K1~K6)
binary_sensor:
  - platform: kc868_ha
    target_relay_controller_addr: 1
    switch_adapter_addr: 10
    bind_output: 1
    name: "Input K1"
    id: input_k1

# 출력 스위치 (D1~D6)
switch:
  - platform: kc868_ha
    target_relay_controller_addr: 1
    switch_adapter_addr: 10
    bind_output: 1
    name: "Output D1"
    id: output_d1
```

## 매개변수 설명

### target_relay_controller_addr
- KC868-HA 보드의 릴레이 컨트롤러 주소
- 기본값: 1
- HA485_Ctrl 소프트웨어의 "Target Relay Controller Addr" 매개변수와 일치해야 함

### switch_adapter_addr
- KC868-HA 보드의 스위치 어댑터 주소
- 기본값: 10
- HA485_Ctrl 소프트웨어의 "Switch Adapter Addr" 매개변수와 일치해야 함

### bind_output
- 바인딩할 출력 번호
- HA485_Ctrl 소프트웨어의 "BindOutput" 매개변수와 일치해야 함
- K1~K6: 1~6, D1~D6: 1~6

## 다중 보드 연결
여러 KC868-HA 보드를 연결할 때는 각 보드마다 다른 `switch_adapter_addr` 값을 사용하세요:

```yaml
# 첫 번째 보드
binary_sensor:
  - platform: kc868_ha
    target_relay_controller_addr: 1
    switch_adapter_addr: 10  # 첫 번째 보드
    bind_output: 1
    name: "Board1 Input K1"

# 두 번째 보드
binary_sensor:
  - platform: kc868_ha
    target_relay_controller_addr: 1
    switch_adapter_addr: 11  # 두 번째 보드
    bind_output: 7
    name: "Board2 Input K1"
```

## 사용 방법

1. **ESP32 준비**: ESP32 개발 보드를 준비합니다.
2. **하드웨어 연결**: ESP32와 KC868-HA 보드를 UART로 연결합니다.
3. **설정 수정**: `kc868-ha-test.yaml` 파일에서 WiFi 정보를 수정합니다.
4. **컴파일 및 업로드**:
   ```bash
   esphome run kc868-ha-test.yaml
   ```
5. **Home Assistant 연결**: Home Assistant에서 자동으로 기기를 감지합니다.

## 문제 해결

### 1. 컴파일 시 경고 메시지
- `BINARY_SENSOR_SCHEMA` 및 `SWITCH_SCHEMA` 경고는 무시해도 됩니다.
- 이는 ESPHome 최신 버전의 스키마 변경으로 인한 것입니다.

### 2. 통신 오류
- UART 연결을 확인하세요 (TX: GPIO 1, RX: GPIO 3).
- baud rate가 9600으로 설정되었는지 확인하세요.
- KC868-HA 보드의 주소 설정을 확인하세요.

### 3. Home Assistant에서 감지되지 않음
- API 설정이 활성화되어 있는지 확인하세요.
- 네트워크 연결을 확인하세요.

## 추가 정보
- 공식 웹사이트: https://www.kincony.com
- GitHub 리포지토리: https://github.com/hzkincony/esphome-kc868-ha
- ESPHome 문서: https://esphome.io/

## 설치 완료!
KC868-HA ESPHome 컴포넌트가 성공적으로 설치되고 테스트되었습니다. 이제 ESP32와 KC868-HA 보드를 연결하여 Home Assistant에서 사용할 수 있습니다! 