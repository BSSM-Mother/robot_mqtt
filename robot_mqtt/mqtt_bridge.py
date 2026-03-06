"""MQTT ↔ ROS2 bridge node.

MQTT topics (subscribe)
-----------------------
robot/command/follow  payload: "true"/"false" or "1"/"0"
                      → publishes /robot/follow_mode (std_msgs/Bool)

robot/command/tts     payload: UTF-8 text string
                      → publishes /robot/tts (std_msgs/String)

ROS2 parameters
---------------
mqtt_host  (string, default: "localhost")
mqtt_port  (int,    default: 1883)
mqtt_keepalive (int, default: 60)
"""

import threading

import paho.mqtt.client as mqtt
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


# ── MQTT topic → ROS2 topic mapping ─────────────────────────────────────────
MQTT_FOLLOW_TOPIC = 'robot/command/follow'
MQTT_TTS_TOPIC = 'robot/command/tts'

ROS_FOLLOW_TOPIC = '/robot/follow_mode'
ROS_TTS_TOPIC = '/robot/tts'


class MqttBridge(Node):
    """Bridges MQTT commands to ROS2 topics."""

    def __init__(self):
        super().__init__('mqtt_bridge')

        # ── ROS2 parameters ──────────────────────────────────────────────────
        self.declare_parameter('mqtt_host', 'localhost')
        self.declare_parameter('mqtt_port', 1883)
        self.declare_parameter('mqtt_keepalive', 60)

        host = self.get_parameter('mqtt_host').get_parameter_value().string_value
        port = self.get_parameter('mqtt_port').get_parameter_value().integer_value
        keepalive = self.get_parameter('mqtt_keepalive').get_parameter_value().integer_value

        # ── ROS2 publishers ──────────────────────────────────────────────────
        self._follow_pub = self.create_publisher(Bool, ROS_FOLLOW_TOPIC, 10)
        self._tts_pub = self.create_publisher(String, ROS_TTS_TOPIC, 10)

        # ── MQTT client setup ────────────────────────────────────────────────
        self._client = mqtt.Client(client_id='ros2_mqtt_bridge')
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        self.get_logger().info(f'Connecting to MQTT broker at {host}:{port}')
        try:
            self._client.connect(host, port, keepalive)
        except Exception as e:
            self.get_logger().error(f'MQTT connection failed: {e}')
            return

        # MQTT 루프를 별도 스레드에서 실행 (ROS2 spin 블로킹 방지)
        self._mqtt_thread = threading.Thread(
            target=self._client.loop_forever, daemon=True)
        self._mqtt_thread.start()

        self.get_logger().info('MQTT Bridge node initialized')

    # ── MQTT callbacks ───────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.get_logger().info('MQTT broker connected')
            client.subscribe(MQTT_FOLLOW_TOPIC)
            client.subscribe(MQTT_TTS_TOPIC)
            self.get_logger().info(
                f'Subscribed: [{MQTT_FOLLOW_TOPIC}], [{MQTT_TTS_TOPIC}]')
        else:
            self.get_logger().error(f'MQTT connection refused (rc={rc})')

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.get_logger().warn(f'MQTT disconnected unexpectedly (rc={rc})')

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='replace').strip()

        if topic == MQTT_FOLLOW_TOPIC:
            self._handle_follow(payload)
        elif topic == MQTT_TTS_TOPIC:
            self._handle_tts(payload)
        else:
            self.get_logger().warn(f'Unknown MQTT topic: {topic}')

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _handle_follow(self, payload: str):
        """Convert payload to Bool and publish to /robot/follow_mode."""
        value = payload.lower() in ('true', '1', 'on', 'yes')
        ros_msg = Bool()
        ros_msg.data = value
        self._follow_pub.publish(ros_msg)
        self.get_logger().info(
            f'[follow_mode] MQTT "{payload}" → ROS2 {value}')

    def _handle_tts(self, payload: str):
        """Forward TTS text to /robot/tts."""
        if not payload:
            return
        ros_msg = String()
        ros_msg.data = payload
        self._tts_pub.publish(ros_msg)
        self.get_logger().info(f'[tts] "{payload}"')

    def destroy_node(self):
        self._client.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MqttBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
