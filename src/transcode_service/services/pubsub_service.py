import json
import logging
from concurrent.futures import TimeoutError
from typing import Callable, Optional

from google.cloud import pubsub_v1
from google.oauth2 import service_account

from ..core.config import settings
from ..models.schemas_v2 import (
    FaceDetectionMessage,
    FaceDetectionResult,
)
from ..models.schemas_v2 import UniversalTranscodeMessage, UniversalTranscodeResult

logger = logging.getLogger(__name__)


class PubSubService:
    def __init__(self):
        self._publisher_client = None
        self._subscriber_client = None
        self.project_id = settings.pubsub_project_id
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of clients"""
        if self._initialized:
            return

        # Check if PubSub is disabled
        if settings.disable_pubsub:
            logger.info("PubSub is disabled, skipping initialization")
            self._initialized = True
            return

        # Check if credentials paths are empty
        if (
                not settings.pubsub_publisher_credentials_path
                or not settings.pubsub_subscriber_credentials_path
        ):
            logger.info("PubSub credentials not configured, skipping initialization")
            self._initialized = True
            return

        logger.info("Initializing PubSub clients...")

        # Publisher credentials
        publisher_credentials = service_account.Credentials.from_service_account_file(
            settings.pubsub_publisher_credentials_path
        )
        self._publisher_client = pubsub_v1.PublisherClient(credentials=publisher_credentials)

        # Subscriber credentials
        subscriber_credentials = service_account.Credentials.from_service_account_file(
            settings.pubsub_subscriber_credentials_path
        )
        self._subscriber_client = pubsub_v1.SubscriberClient(credentials=subscriber_credentials)

        # Topic transcode paht (original)
        self.transcode_task_topic_path = self._publisher_client.topic_path(
            self.project_id, settings.pubsub_transcode_task_topic
        )
        # Topic paths (original)
        self.results_topic_path = self._publisher_client.topic_path(
            self.project_id, settings.pubsub_results_topic
        )

        self.universal_tasks_topic_path = self._publisher_client.topic_path(
            self.project_id,
            settings.pubsub_tasks_topic
        )
        self.universal_results_topic_path = self._publisher_client.topic_path(
            self.project_id,
            settings.pubsub_results_topic
        )

        # Face detection topic paths (using same topics or add new ones if
        # needed)
        self.face_detection_tasks_topic_path = self._publisher_client.topic_path(
            self.project_id,
            settings.pubsub_face_detection_tasks_topic
        )
        self.face_detection_results_topic_path = self._publisher_client.topic_path(
            self.project_id,
            settings.pubsub_face_detection_results_topic
        )

        # Subscription paths
        self.tasks_subscription_path = self._subscriber_client.subscription_path(
            self.project_id, settings.tasks_subscription
        )
        self.results_subscription_path = self._subscriber_client.subscription_path(
            self.project_id, settings.pubsub_results_subscription
        )

        # Face detection results subscription path
        face_detection_results_subscription = settings.pubsub_face_detection_results_subscription
        self.face_detection_results_subscription_path = self._subscriber_client.subscription_path(
            self.project_id, face_detection_results_subscription
        )
        self._initialized = True
        logger.info("PubSub clients initialized successfully")

    @property
    def publisher_client(self):
        self._lazy_init()
        return self._publisher_client

    @property
    def subscriber_client(self):
        self._lazy_init()
        return self._subscriber_client

    def _is_disabled(self) -> bool:
        """Check if PubSub is disabled"""
        return settings.disable_pubsub or not settings.pubsub_publisher_credentials_path

    def publish_universal_transcode_task(self, message: UniversalTranscodeMessage) -> str:
        """Publish universal transcode task to Pub/Sub v2"""
        try:
            if self._is_disabled():
                logger.warning("PubSub is disabled, skipping publish_universal_transcode_task")
                return "disabled"

            data = message.model_dump_json().encode("utf-8")

            future = self.publisher_client.publish(
                self.transcode_task_topic_path,
                data,
                task_id=message.task_id,
                profile_id=message.profile.id_profile,
            )

            message_id = future.result()
            logger.info(
                f"Published universal transcode task: {message.task_id}, message_id: {message_id}"
            )
            return message_id

        except Exception as e:
            logger.error(f"Error publishing universal transcode task: {self.transcode_task_topic_path} {e}")
            raise

    def publish_universal_transcode_result(self, result: UniversalTranscodeResult) -> str:
        """Publish universal transcode result to Pub/Sub v2"""
        try:
            if self._is_disabled():
                logger.warning("PubSub is disabled, skipping publish_universal_transcode_result")
                return "disabled"

            data = result.model_dump_json().encode("utf-8")

            future = self.publisher_client.publish(
                self.universal_results_topic_path,
                data,
                task_id=result.task_id,
                profile_id=result.profile_id,
            )

            message_id = future.result()
            logger.info(
                f"Published universal transcode result: {result.task_id}, message_id: {message_id}"
            )
            return message_id

        except Exception as e:
            logger.error(f"Error publishing universal transcode result: {e}")
            raise

    def listen_for_transcode_messages(self, callback: Callable, timeout: Optional[float] = None):
        """Subscribe to universal transcode tasks (v2 system)"""
        if self._is_disabled():
            logger.info("PubSub is disabled, skipping universal transcode task subscription")
            return

        # Use universal tasks subscription
        subscription_name = settings.transcode_task_subscription

        if not subscription_name:
            logger.info("Universal tasks subscription name not configured, skipping listener")
            return

        subscription_path = self.subscriber_client.subscription_path(
            self.project_id, subscription_name
        )

        logger.info("🎧 Setting up universal transcode subscriber...")
        logger.info(f"📍 Project ID: {self.project_id}")
        logger.info(f"📬 Subscription name: {subscription_name}")
        logger.info(f"🔗 Full subscription path: {subscription_path}")
        logger.info(f"📨 Universal tasks topic: {self.universal_tasks_topic_path}")

        def message_callback(message):
            try:
                data = json.loads(message.data.decode("utf-8"))
                universal_message = UniversalTranscodeMessage(**data)

                logger.info(f"📥 Received universal transcode task: {universal_message.task_id}")
                logger.info(f"🔗 Source URL: {universal_message.source_url}")
                logger.info(f"⚙️ Profile: {universal_message.profile.id_profile}")

                callback(universal_message)

                message.ack()
                logger.info(f"✅ Acknowledged universal transcode message: {universal_message.task_id}")

            except Exception as e:
                logger.error(f"❌ Error processing universal transcode message: {e}")
                message.nack()

        flow_control = pubsub_v1.types.FlowControl(max_messages=2)

        streaming_pull_future = self.subscriber_client.subscribe(
            subscription_path, callback=message_callback, flow_control=flow_control
        )

        logger.info(f"🎧 Listening for universal transcode messages on {subscription_path}")

        with self.subscriber_client:
            try:
                streaming_pull_future.result(timeout=timeout)
            except TimeoutError:
                streaming_pull_future.cancel()
                streaming_pull_future.result()

    def publish_face_detection_task(self, message: FaceDetectionMessage) -> str:
        """Publish face detection task to Pub/Sub"""
        try:
            data = message.model_dump_json().encode("utf-8")

            logger.info(
                f"🔤 Publishing face detection task to topic: {self.face_detection_tasks_topic_path}"
            )
            logger.info(
                f"📋 Face detection task details - task_id: {message.task_id}, source_url: {message.source_url}"
            )
            logger.info(f"⚙️ Face detection config: {message.config}")

            future = self.publisher_client.publish(
                self.face_detection_tasks_topic_path, data, task_id=message.task_id
            )

            message_id = future.result()
            return message_id

        except Exception as e:
            logger.error(f"Error publishing face detection task: {e}")
            raise

    def publish_face_detection_result(self, result: FaceDetectionResult) -> str:
        """Publish face detection result to Pub/Sub"""
        try:
            data = result.model_dump_json().encode("utf-8")

            future = self.publisher_client.publish(
                self.face_detection_results_topic_path, data, task_id=result.task_id
            )

            message_id = future.result()
            logger.info(
                f"Published face detection result: {result.task_id}, message_id: {message_id}"
            )
            return message_id

        except Exception as e:
            logger.error(f"Error publishing face detection result: {e}")
            raise

    async def publish_message(self, topic: str, message: dict) -> bool:
        """Publish a message to a specific topic"""
        try:
            self._lazy_init()

            # Create topic path
            topic_path = self._publisher_client.topic_path(self.project_id, topic)

            # Serialize message
            message_data = json.dumps(message).encode("utf-8")

            # Publish message
            logger.info(f"Publishing message to topic {topic}")
            future = self._publisher_client.publish(topic_path, message_data)

            # Wait for result
            future.result()

            logger.info(f"Published message to topic {topic}")
            return True

        except Exception as e:
            logger.error(f"Error publishing message to topic {topic}: {e}")
            return False

    def listen_for_face_detection_messages(
            self, subscription_name: str, callback: Callable, timeout: Optional[float] = None
    ):
        """Subscribe to face detection messages"""
        if self._is_disabled():
            logger.info("PubSub is disabled, skipping face detection message listener")
            return

        if not subscription_name:
            logger.info("Face detection subscription name not configured, skipping listener")
            return

        subscription_path = self.subscriber_client.subscription_path(
            self.project_id, subscription_name
        )

        logger.info("🎧 Setting up face detection subscriber...")
        logger.info(f"📍 Project ID: {self.project_id}")
        logger.info(f"📬 Subscription name: {subscription_name}")
        logger.info(f"🔗 Full subscription path: {subscription_path}")
        logger.info(
            f"📨 Face detection tasks topic: {self.face_detection_tasks_topic_path}"
        )

        def message_callback(message):
            try:
                data = json.loads(message.data.decode("utf-8"))
                face_detection_message = FaceDetectionMessage(**data)

                logger.info(
                    f"📥 Received face detection task: {face_detection_message.task_id}"
                )
                logger.info(
                    f"🔗 Source URL: {face_detection_message.source_url}"
                )
                logger.info(f"⚙️ Config: {face_detection_message.config}")

                callback(face_detection_message)

                message.ack()
                logger.info(
                    f"✅ Acknowledged face detection message: {face_detection_message.task_id}"
                )

            except Exception as e:
                logger.error(f"❌ Error processing face detection message: {e}")
                message.nack()

        flow_control = pubsub_v1.types.FlowControl(max_messages=5)

        streaming_pull_future = self.subscriber_client.subscribe(
            subscription_path, callback=message_callback, flow_control=flow_control
        )

        logger.info(f"🎧 Listening for face detection messages on {subscription_path}")

        with self.subscriber_client:
            try:
                streaming_pull_future.result(timeout=timeout)
            except TimeoutError:
                streaming_pull_future.cancel()
                streaming_pull_future.result()

    def pull_face_detection_results(self, max_messages: int = 10) -> list[FaceDetectionResult]:
        """Pull face detection results (for testing/manual processing)"""
        try:
            response = self.subscriber_client.pull(
                request={
                    "subscription": self.face_detection_results_subscription_path,
                    "max_messages": max_messages,
                    "return_immediately": True,  # Don't wait if no messages
                }
            )

            results = []
            ack_ids = []

            for received_message in response.received_messages:
                try:
                    data = json.loads(received_message.message.data.decode("utf-8"))
                    result = FaceDetectionResult(**data)
                    results.append(result)
                    ack_ids.append(received_message.ack_id)
                except Exception as e:
                    logger.error(f"Error parsing face detection result message: {e}")

            if ack_ids:
                self.subscriber_client.acknowledge(
                    request={
                        "subscription": self.face_detection_results_subscription_path,
                        "ack_ids": ack_ids,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error pulling face detection results: {e}")
            return []

    def pull_universal_results(self, max_messages: int = 10) -> list:
        """Pull universal transcode results (v2) for testing/manual processing"""
        try:
            # Use universal results subscription path
            subscription_path = self.subscriber_client.subscription_path(
                self.project_id,
                settings.pubsub_results_subscription
            )

            response = self.subscriber_client.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": max_messages,
                    "return_immediately": True,  # Don't wait if no messages
                }
            )

            results = []
            ack_ids = []

            for received_message in response.received_messages:
                try:
                    data = json.loads(received_message.message.data.decode("utf-8"))
                    result = UniversalTranscodeResult(**data)
                    results.append(result)
                    ack_ids.append(received_message.ack_id)
                except Exception as e:
                    logger.error(f"Error parsing universal result message: {e}")

            if ack_ids:
                self.subscriber_client.acknowledge(
                    request={
                        "subscription": subscription_path,
                        "ack_ids": ack_ids,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error pulling universal results: {e}")
            return []


pubsub_service = PubSubService()
