from aiokafka.admin import AIOKafkaAdminClient,NewTopic
from aiokafka.errors import TopicAlreadyExistsError
async def create_topics(settings):
    admin=AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers); await admin.start()
    try:
        topics=[NewTopic(name=settings.kafka_topic,num_partitions=settings.kafka_test_partitions,replication_factor=1,topic_configs={"cleanup.policy":"delete","retention.ms":"120000"}),NewTopic(name="study-group-chat",num_partitions=settings.kafka_chat_partitions,replication_factor=1,topic_configs={"cleanup.policy":"delete","retention.ms":"86400000"})]
        for topic in topics:
            try: await admin.create_topics([topic])
            except TopicAlreadyExistsError: pass
    finally: await admin.close()
