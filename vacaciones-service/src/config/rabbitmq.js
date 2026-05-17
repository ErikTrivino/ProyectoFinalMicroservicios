const amqp = require('amqplib');

class RabbitMQConfig {
  constructor() {
    this.connection = null;
    this.channel = null;
    this.exchange = 'empleados_events';
    this.url = process.env.RABBITMQ_URL || `amqp://${process.env.RABBITMQ_USER || 'admin'}:${process.env.RABBITMQ_PASS || 'admin'}@${process.env.RABBITMQ_HOST || 'localhost'}:${process.env.RABBITMQ_PORT || 5672}`;
  }

  async connect() {
    try {
      this.connection = await amqp.connect(this.url);
      this.channel = await this.connection.createChannel();
      await this.channel.assertExchange(this.exchange, 'fanout', { durable: true });
      console.log('Conectado a RabbitMQ exitosamente (Exchange: empleados_events, Tipo: fanout).');
    } catch (error) {
      console.error('Error conectando a RabbitMQ:', error);
      // Reintentar conexión en 5 segundos
      setTimeout(() => this.connect(), 5000);
    }
  }

  async publishEvent(routingKey, message) {
    if (!this.channel) {
      console.error('No hay canal de RabbitMQ disponible para publicar.');
      return;
    }
    try {
      const msgBuffer = Buffer.from(JSON.stringify(message));
      this.channel.publish(this.exchange, routingKey, msgBuffer);
      console.log(`Evento publicado [${routingKey}]:`, message);
    } catch (error) {
      console.error('Error publicando evento:', error);
    }
  }
}

const rabbitMQ = new RabbitMQConfig();
module.exports = rabbitMQ;
