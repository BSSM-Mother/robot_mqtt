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
                               default: ENV ROBOT_STATE_API_URL
                               fallback: 없음(미설정 시 폴링 안 함)
    poll_interval_s  (double)  폴링 주기 (초), default: 1.0
    request_timeout  (double)  HTTP 타임아웃 (초), default: 2.0
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
import os

import requests


class ApiBridge(Node):

    def __init__(self):
        super().__init__('api_bridge')

        # ── 파라미터 ──────────────────────────────────────────
        default_api_url = os.getenv(
            'ROBOT_STATE_API_URL',
            '')
        self.declare_parameter('api_url',
                               default_api_url)
        self.declare_parameter('poll_interval_s', 1.0)
        self.declare_parameter('request_timeout', 2.0)

        param_api_url = (self.get_parameter('api_url')
                         .get_parameter_value().string_value)
        self._url = param_api_url or default_api_url
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
        if not self._url:
            self.get_logger().warn(
                'API URL 미설정: ROBOT_STATE_API_URL 또는 ROS 파라미터 api_url 설정 필요')

    @staticmethod
    def _to_bool(value) -> bool:
        """Convert typical API flag values (0/1, true/false, strings) to bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {'1', 'true', 'on', 'yes', 'y'}:
                return True
            if normalized in {'0', 'false', 'off', 'no', 'n', ''}:
                return False
        return bool(value)

    # ──────────────────────────────────────────────────────────

    def _poll(self):
        if not self._url:
            return

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
        follow = self._to_bool(data.get('follow', False))
        msg = Bool()
        msg.data = follow
        self._follow_pub.publish(msg)

        # ── buzzer: rising edge(false→true) 에서만 트리거 ──────
        buzzer = self._to_bool(data.get('buzzer', False))
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
