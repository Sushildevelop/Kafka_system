from aiokafka.admin import AIOKafkaAdminClient, NewTopic

async def create_topics(settings):
    admin = AIOKafkaAdminClient(
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )

    await admin.start()

    try:
        topic = NewTopic(
            name=settings.kafka_topic,
            num_partitions=settings.kafka_test_partitions,
            replication_factor=1,
            topic_configs={
                "cleanup.policy": "delete",
                "retention.ms": "120000",
            },
        )

        await admin.create_topics([topic])

    finally:
        await admin.close()