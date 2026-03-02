"""RabbitMQ 消息队列服务"""
import pika
import json
import time
from typing import Dict, Callable
from app.core.config import settings


class RabbitMQService:
    """RabbitMQ 服务"""
    
    def __init__(self):
        self.url = settings.RABBITMQ_URL
        self.queue_name = settings.QUEUE_NAME
        self.dlq_name = settings.DLQ_NAME
        self.connection = None
        self.channel = None
        self.max_retries = 3
        self.retry_delay = 2  # 秒
    
    def connect(self):
        """建立连接（带重试机制）"""
        for attempt in range(self.max_retries):
            try:
                # 检查现有连接
                if self.connection and not self.connection.is_closed:
                    if self.channel and self.channel.is_open:
                        return  # 连接正常
                
                # 关闭旧连接
                self._close_connection()
                
                # 创建新连接（添加心跳和超时配置）
                params = pika.URLParameters(self.url)
                params.heartbeat = 600  # 10分钟心跳
                params.blocked_connection_timeout = 300  # 5分钟阻塞超时
                params.connection_attempts = 3
                params.retry_delay = 2
                
                self.connection = pika.BlockingConnection(params)
                self.channel = self.connection.channel()
                
                # 声明死信队列
                self.channel.queue_declare(
                    queue=self.dlq_name,
                    durable=True
                )
                
                # 声明主队列（带死信配置）
                self.channel.queue_declare(
                    queue=self.queue_name,
                    durable=True,
                    arguments={
                        'x-dead-letter-exchange': '',
                        'x-dead-letter-routing-key': self.dlq_name
                    }
                )
                
                print(f"RabbitMQ connected successfully (attempt {attempt + 1})")
                return
                
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"Failed to connect to RabbitMQ after {self.max_retries} attempts")
    
    def _close_connection(self):
        """安全关闭连接"""
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
        except:
            pass
        
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except:
            pass
        
        self.channel = None
        self.connection = None
    
    def publish(self, message: Dict) -> bool:
        """
        发布消息到队列（带重试机制）
        
        Args:
            message: 消息内容
            
        Returns:
            是否成功
        """
        for attempt in range(self.max_retries):
            try:
                self.connect()
                
                self.channel.basic_publish(
                    exchange='',
                    routing_key=self.queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # 持久化
                        content_type='application/json'
                    )
                )
                return True
                
            except (pika.exceptions.AMQPConnectionError, 
                    pika.exceptions.AMQPChannelError,
                    pika.exceptions.StreamLostError) as e:
                print(f"Publish attempt {attempt + 1} failed: {e}")
                self._close_connection()
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    print(f"Failed to publish message after {self.max_retries} attempts")
                    return False
                    
            except Exception as e:
                print(f"Unexpected error publishing message: {e}")
                return False
    
    def consume(self, callback: Callable, prefetch_count: int = 1):
        """
        消费队列消息（带自动重连）
        
        Args:
            callback: 消息处理回调函数
            prefetch_count: 预取数量（并发控制）
        """
        while True:
            try:
                self.connect()
                
                # 设置 QoS（并发控制）
                self.channel.basic_qos(prefetch_count=prefetch_count)
                
                def on_message(ch, method, properties, body):
                    """消息处理包装器"""
                    try:
                        message = json.loads(body)
                        
                        # 调用回调处理消息
                        success = callback(message)
                        
                        if success:
                            # 确认消息
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                        else:
                            # 拒绝消息，重新入队
                            ch.basic_nack(
                                delivery_tag=method.delivery_tag,
                                requeue=True
                            )
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        # 拒绝消息，不重新入队（进入死信队列）
                        ch.basic_nack(
                            delivery_tag=method.delivery_tag,
                            requeue=False
                        )
                
                self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=on_message
                )
                
                print(f"Started consuming from queue: {self.queue_name}")
                self.channel.start_consuming()
                
            except (pika.exceptions.AMQPConnectionError,
                    pika.exceptions.AMQPChannelError,
                    pika.exceptions.StreamLostError) as e:
                print(f"Connection lost during consume: {e}")
                print("Reconnecting in 5 seconds...")
                self._close_connection()
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("Stopping consumer...")
                break
                
            except Exception as e:
                print(f"Unexpected error in consumer: {e}")
                time.sleep(5)
    
    def close(self):
        """关闭连接"""
        print("Closing RabbitMQ connection...")
        self._close_connection()


# 全局实例
rabbitmq_service = RabbitMQService()
