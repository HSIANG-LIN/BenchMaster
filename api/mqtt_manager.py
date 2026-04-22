# ~/benchmaster/api/mqtt_manager.py

import json
import logging
import threading
import paho.mqtt.client as mqtt
from db.models import get_engine, get_session, Machine

logger = logging.getLogger("MqttManager")

class MqttManager:
    def __init__(self, broker="broker.emqx.io", port=1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.engine = get_engine()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("Successfully connected to MQTT Broker.")
            self.client.subscribe("benchmaster/agent/+/status")
            self.client.subscribe("benchmaster/agent/+/metrics")
        else:
            logger.error(f"Failed to connect to MQTT Broker (code {rc})")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        logger.warning("Disconnected from MQTT Broker.")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            logger.info(f"MQTT Message received on {topic}: {payload}")

            parts = topic.split("/")
            if len(parts) == 4:
                machine_id = int(parts[2])
                if "status" in topic:
                    self._update_machine_status(machine_id, payload)
                elif "metrics" in topic:
                    self._update_machine_metrics(machine_id, payload)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _update_machine_status(self, machine_id, payload):
        session = get_session(self.engine)
        try:
            machine = session.query(Machine).filter(Machine.id == machine_id).first()
            if machine:
                machine.status = payload.get("status", "ONLINE")
                session.commit()
                logger.info(f"Updated Machine {machine_id} status to {machine.status} via MQTT.")
            else:
                logger.warning(f"Received status for unknown Machine ID: {machine_id}")
        except Exception as e:
            logger.error(f"Failed to update machine status in DB: {e}")
        finally:
            session.close()

    def _update_machine_metrics(self, machine_id, payload):
        session = get_session(self.engine)
        try:
            machine = session.query(Machine).filter(Machine.id == machine_id).first()
            if machine:
                # Update real-time metrics
                machine.cpu_usage_percent = payload.get("cpu_usage_percent", machine.cpu_usage_percent)
                machine.memory_used_mb = payload.get("memory_used_mb", machine.memory_used_mb)
                machine.memory_total_mb = payload.get("memory_total_mb", machine.memory_total_mb)
                machine.disk_usage_percent = payload.get("disk_usage_percent", machine.disk_usage_percent)
                machine.network_rx_mbps = payload.get("network_rx_mbps", machine.network_rx_mbps)
                machine.network_tx_mbps = payload.get("network_tx_mbps", machine.network_tx_mbps)
                # last_metrics_update is handled by onupdate=get_utc_now in models.py
                
                session.commit()
                logger.info(f"Updated Machine {machine_id} metrics via MQTT.")
            else:
                logger.warning(f"Received metrics for unknown Machine ID: {machine_id}")
        except Exception as e:
            logger.error(f"Failed to update machine metrics in DB: {e}")
        finally:
            session.close()

    def publish_task(self, machine_id, task_data):
        topic = f"benchmaster/agent/{machine_id}/tasks"
        payload = json.dumps(task_data)
        result = self.client.publish(topic, payload, qos=1)
        logger.info(f"Published task to {topic}: {payload}")
        return result

    def start(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logger.info(f"MQTT Manager started on {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Could not start MQTT Manager: {e}")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT Manager stopped.")

mqtt_manager = MqttManager()
