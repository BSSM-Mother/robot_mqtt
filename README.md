# robot_mqtt - MQTT 통신 브릿지

**MQTT 프로토콜을 통해 외부 시스템과 로봇을 연결하는 통신 패키지**

## 📌 개요

MQTT 브로커와 ROS2 토픽을 양방향으로 연결하여, 외부 애플리케이션(모바일 앱, 웹 서버 등)에서 로봇을 원격 제어하고 상태 정보를 받을 수 있습니다.

## 🎯 주요 기능

- ✅ **ROS2 ↔ MQTT 양방향 통신**
- ✅ **콘솔/모바일 앱에서 원격 제어**
- ✅ **로봇 상태 실시간 모니터링**
- ✅ **자동 재연결 기능**

## 🔗 MQTT 토픽 맵핑

### ROS2 → MQTT (발행)

로봇에서 외부로 보내는 데이터:

| ROS2 토픽 | MQTT 토픽 | 메시지 타입 | 설명 |
|---------|----------|----------|------|
| `/person_position` | `robot/person_position` | Point (JSON) | 감지된 사람 위치 |
| `/cmd_vel_raw` | `robot/cmd_vel` | Twist (JSON) | 현재 속도 명령 |
| `/scan` | `robot/scan` | LaserScan | LIDAR 거리 데이터 |

### MQTT → ROS2 (구독)

외부에서 로봇으로 보내는 명령:

| MQTT 토픽 | ROS2 토픽 | 메시지 타입 | 설명 |
|---------|---------|----------|------|
| `robot/cmd_vel` | `/cmd_vel_raw` | Twist | 속도 명령 |
| `robot/follow_mode` | `/robot/follow_mode` | Bool | 추적 모드 ON/OFF |
| `robot/control_cmd` | `/robot/control` | String | 기타 제어 명령 |

## ⚙️ MQTT 브로커 설정

### 연결 파라미터

```yaml
mqtt_bridge:
  ros__parameters:
    broker_host: "localhost"       # MQTT 브로커 주소
    broker_port: 1883             # MQTT 포트
    client_id: "robot_01"         # 클라이언트 ID
    username: "robot"             # 사용자명 (선택)
    password: "password123"       # 비밀번호 (선택)
    qos: 0                        # QoS 레벨 (0, 1, 2)
    keepalive: 60                 # 킵얼라이브 간격 (초)
```

### QoS 레벨

- **0 (At Most Once)**: 빠르지만 메시지 손실 가능 (상태 정보용)
- **1 (At Least Once)**: 메시지 보장, 중복 가능 (명령용)
- **2 (Exactly Once)**: 정확히 한 번 전달 (중요 명령용)

## 📊 MQTT 메시지 형식

### JSON 형식 (권장)

```json
/* 속도 명령 */
{
  "linear": {"x": 0.5, "y": 0, "z": 0},
  "angular": {"x": 0, "y": 0, "z": 0.3}
}

/* 사람 위치 */
{
  "x": 0.2,
  "y": -0.1,
  "z": 0.85
}

/* 상태 메시지 */
{
  "status": "tracking",
  "battery": 85,
  "mode": "autonomous"
}
```

## 🚀 실행

개별 실행:
```bash
ros2 run robot_mqtt mqtt_bridge_node
```

또는 런치 파일로:
```bash
ros2 launch robot_launch robot.launch.py
```

## 💻 외부 클라이언트 예시

### Python MQTT 클라이언트

```python
import paho.mqtt.client as mqtt
import json

class RobotController:
    def __init__(self, broker_host="localhost"):
        self.client = mqtt.Client("controller")
        self.client.connect(broker_host, 1883, 60)
        self.client.on_message = self.on_message
        self.client.subscribe("robot/person_position")

    def send_command(self, linear_x, angular_z):
        """로봇에 속도 명령 전송"""
        cmd = {
            "linear": {"x": linear_x},
            "angular": {"z": angular_z}
        }
        self.client.publish("robot/cmd_vel", json.dumps(cmd))

    def on_message(self, client, userdata, msg):
        """MQTT 메시지 수신"""
        print(f"Topic: {msg.topic}, Message: {msg.payload.decode()}")

    def run(self):
        self.client.loop_start()

        # 예: 로봇 전진
        self.send_command(linear_x=0.5, angular_z=0.0)

if __name__ == "__main__":
    robot = RobotController()
    robot.run()
```

### Node.js/JavaScript 클라이언트

```javascript
const mqtt = require('mqtt');

const client = mqtt.connect('mqtt://localhost:1883');

client.on('connect', () => {
  console.log('MQTT Connected');

  // 속도 명령 전송
  const cmd = {
    linear: { x: 0.5 },
    angular: { z: 0.0 }
  };
  client.publish('robot/cmd_vel', JSON.stringify(cmd));

  // 상태 구독
  client.subscribe('robot/person_position', (err) => {
    if (!err) console.log('Subscribed to person_position');
  });
});

client.on('message', (topic, message) => {
  console.log(`[${topic}] ${message.toString()}`);
});
```

## 📱 모바일 앱 예시 (React Native)

```javascript
import mqtt from 'react-native-mqtt';

class RobotApp extends Component {
  constructor(props) {
    super(props);
    this.client = new mqtt.Client({
      uri: 'mqtt://192.168.1.100:1883',
      clientId: 'mobile_app'
    });

    this.client.on('connect', this.onConnect);
    this.client.on('message', this.onMessage);
    this.client.connect();
  }

  onConnect = () => {
    this.client.subscribe('robot/person_position');
  }

  sendCommand = (speed) => {
    const cmd = {
      linear: { x: speed },
      angular: { z: 0 }
    };
    this.client.publish('robot/cmd_vel', JSON.stringify(cmd));
  }

  onMessage = (msg) => {
    console.log(msg);
  }
}
```

## 🌐 HTTP REST API 대안

MQTT 대신 HTTP를 사용하려면:

```bash
ros2 run rosbridge_server rosbridge_websocket
# http://192.168.1.100:9090/
```

## 🔒 보안 설정

### SSL/TLS 암호화

```python
client.tls_set(
    ca_certs="/etc/mqtt/ca.crt",
    certfile="/etc/mqtt/client.crt",
    keyfile="/etc/mqtt/client.key"
)
```

### Mosquitto 브로커 설정 (server)

```yaml
# /etc/mosquitto/mosquitto.conf
listener 8883
cafile /etc/mosquitto/ca.crt
certfile /etc/mosquitto/server.crt
keyfile /etc/mosquitto/server.key
```

## 📊 네트워크 구성

```
┌─────────────────┐
│   모바일 앱     │
└────────┬────────┘
         │ MQTT 통신
         ▼
┌──────────────────────┐
│  MQTT 브로커         │ (mosquitto, HiveMQ 등)
│  (192.168.1.100)     │
└────────┬─────────────┘
         │ 로컬 네트워크
         ▼
┌──────────────────────┐
│  로봇 (ROS2)         │
│  192.168.1.50        │
│  robot_mqtt 노드     │
└──────────────────────┘
```

## ⚠️ 주의사항

- **보안**: 인터넷 노출 시 반드시 인증/암호화 설정
- **네트워크 지연**: MQTT 특성상 약 100ms 지연 (실시간 제어 곤란)
- **메시지 손실**: QoS 0 사용 시 메시지 손실 가능
- **브로커 위치**: 로컬 네트워크 또는 클라우드 MQTT 서비스 사용 가능

## 🔗 연관 패키지

- **입력 출처**: robot_control, robot_perception
- **출력 대상**: robot_control (명령 수신)
- **의존성**: rclpy, paho-mqtt, std_msgs

## 📚 유용한 명령어

```bash
# MQTT 토픽 모니터링 (터미널)
mosquitto_sub -h localhost -t "robot/#"

# MQTT 메시지 발행 (테스트)
mosquitto_pub -h localhost -t "robot/cmd_vel" -m '{"linear":{"x":0.5}}'

# Mosquitto 브로커 시작
mosquitto -c /etc/mosquitto/mosquitto.conf
```

## 🚀 배포 옵션

### 옵션 1: 로컬 네트워크
- 홈 네트워크, 오피스 LANMosquitto 브로커 설치
- 간편하지만 인터넷 접근 불가

### 옵션 2: 클라우드 MQTT
- AWS IoT, Azure IoT Hub, HiveMQ Cloud
- 어디서든 원격 접근 가능
- 보안 및 비용 고려

### 옵션 3: VPN + 로컬 브로커
- 보안성과 편의성 균형
- WireGuard, OpenVPN 등 활용
