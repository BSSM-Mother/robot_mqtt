from setuptools import find_packages, setup

package_name = 'robot_mqtt'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='bitbyte08',
    maintainer_email='me@bitworkspace.kr',
    description='MQTT to ROS2 bridge node',
    license='TODO',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mqtt_bridge = robot_mqtt.mqtt_bridge:main',  # 구버전 (미사용)
            'api_bridge = robot_mqtt.api_bridge:main',
        ],
    },
)
