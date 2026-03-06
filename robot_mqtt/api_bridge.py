"""HTTP API polling → ROS2 bridge node.

서버 API (GET /api/robot/state) 를 주기적으로 폴링하여
ROS2 토픽으로 변환 발행한다.

API 응답 형식 (JSON):
    {
        "follow": true,      // 추적 모드 on/off
        "buzzer": false      // true 로 변하는 순간(rising edge) 부저 1회 트리거
    }

ROS2 topics published:
    /robot/follow_mode  (std_msgs/Bool)
    /robot/buzzer       (std_msgs/Bool)  — rising edge 시 True 1회 발행

ROS2 parameters:
    api_url          (string)  폴링할 전체 URL
                               default: "http://localhost:5000/api/robot/state"
    poll_interval_s  (double)  폴링 주기 (초), default: 1.0
    request_timeout  (double)  HTTP 타임아웃 (초), default: 2.0
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

import requests


class ApiBridge(Node):

    def __init__(self):
        super().__init__('api_bridge')

        # ── 파라미터 ──────────────────────────────────────────
        self.declare_parameter('api_url',
                               'http://localhost:5000/api/robot/state')
        self.declare_parameter('poll_interval_s', 1.0)
        self.declare_parameter('request_timeout', 2.0)

        self._url = (self.get_parameter('api_url')
                     .get_parameter_value().string_value)
        interval = (self.get_parameter('poll_interval_s')
                    .get_parameter_value().double_value)
        self._timeout = (self.get_parameter('request_timeout')
                         .get_parameter_value().double_value)

        # ── 퍼블리셔 ──────────────────────────────────────────
        self._follow_pub = self.create_publisher(Bool, '/robot/follow_mode', 10)
        self._buzzer_pub = self.create_publisher(Bool, '/robot/buzzer', 10)

        # ── 이전 상태 (rising edge 감지용) ────────────────────
        self._prev_buzzer = False

        # ── 폴링 타이머 ───────────────────────────────────────
        self._timer = self.create_timer(interval, self._poll)

        self.get_logger().info(
            f'ApiBridge 시작 — URL: {self._url}  주기: {interval}s')

    # ──────────────────────────────────────────────────────────

    def _poll(self):
        try:
            resp = requests.get(self._url, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            self.get_logger().warn('API 서버 연결 실패, 재시도 중...', throttle_duration_sec=5.0)
            return
        except Exception as e:
            self.get_logger().warn(f'API 응답 오류: {e}', throttle_duration_sec=5.0)
            return

        # ── follow_mode ────────────────────────────────────────
        follow = bool(data.get('follow', False))
        msg = Bool()
        msg.data = follow
        self._follow_pub.publish(msg)

        # ── buzzer: rising edge(false→true) 에서만 트리거 ──────
        buzzer = bool(data.get('buzzer', False))
        if buzzer and not self._prev_buzzer:
            trig = Bool()
            trig.data = True
            self._buzzer_pub.publish(trig)
            self.get_logger().info('부저 트리거')
        self._prev_buzzer = buzzer


def main(args=None):
    rclpy.init(args=args)
    node = ApiBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
